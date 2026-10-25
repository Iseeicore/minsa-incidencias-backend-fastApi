from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Body, Depends

from app.constants.textos.incidencias import MENSAJE_ACCION_REALIZADA
from app.enums.accion_incidencia import AccionIncidencia
from app.enums.error_code import ErrorCode
from app.enums.vista_codigo import VistaCodigo
from app.incidencias.adapters.http.ejemplos import DETALLE_EJEMPLO
from app.incidencias.adapters.http.parametros_de_ruta import codigo_de_incidencia
from app.incidencias.adapters.http.schemas_de_accion import (
    ArchivoRequest,
    CasoEnviadoAOtransResponse,
    CorreccionRequest,
    DerivacionRequest,
    ReaperturaRequest,
    ResolucionRequest,
    ResultadoDeAccionResponse,
    SinDatosRequest,
)
from app.incidencias.application.acciones import Confirmar, Tomar
from app.incidencias.domain.resultado_de_accion import CasoEnviadoAOtrans
from app.shared.auth_deps import require_vista
from app.shared.http_errors import (
    INTERNAL_RESPONSE,
    PAYLOAD_TOO_LARGE_RESPONSE,
    RATE_LIMITED_RESPONSE,
    SIN_SESION_RESPONSE,
    VALIDATION_RESPONSE,
    error_response,
    json_example,
)
from app.shared.sesion import SesionActual

if TYPE_CHECKING:
    from app.incidencias.application.ejecutar_accion import EjecutarAccion
    from app.incidencias.domain.resultado_de_accion import ResultadoDeAccion

FORBIDDEN_RESPONSE = error_response(HTTPStatus.FORBIDDEN, ErrorCode.FORBIDDEN)
NOT_FOUND_RESPONSE = error_response(HTTPStatus.NOT_FOUND, ErrorCode.NOT_FOUND)
CONFLICT_RESPONSE = error_response(HTTPStatus.CONFLICT, ErrorCode.CONFLICT)
UNPROCESSABLE_RESPONSE = error_response(HTTPStatus.UNPROCESSABLE_ENTITY, ErrorCode.UNPROCESSABLE)
COMUNES = {**SIN_SESION_RESPONSE, **RATE_LIMITED_RESPONSE, **INTERNAL_RESPONSE}

INICIO = "Exige la vista CASOS. "
CIERRE = (
    " Corre en una transacción firmada con el actor usuario:{correo}, bloquea el caso y recalcula las acciones "
    "permitidas para los roles de la sesión en el estado actual. Responde { mensaje, caso }; caso es null si la "
    "acción lo saca de la vista de quien la hizo."
)

CasosDep = Annotated[SesionActual, Depends(require_vista(VistaCodigo.CASOS))]
CodigoDep = Annotated[str, Depends(codigo_de_incidencia)]
Resultado = ResultadoDeAccionResponse | CasoEnviadoAOtransResponse


def cuerpo_vacio(cuerpo: Annotated[SinDatosRequest | None, Body()] = None) -> SinDatosRequest:
    return cuerpo if cuerpo is not None else SinDatosRequest()


CuerpoVacioDep = Annotated[SinDatosRequest, Depends(cuerpo_vacio)]


def _respuestas(accion: AccionIncidencia, *, con_no_procesable: bool = True) -> dict[int | str, dict[str, object]]:
    exito: dict[int | str, dict[str, object]] = {
        HTTPStatus.OK: {
            "description": "Acción realizada.",
            "content": json_example({"mensaje": MENSAJE_ACCION_REALIZADA[accion], "caso": DETALLE_EJEMPLO}),
        }
    }
    no_procesable = UNPROCESSABLE_RESPONSE if con_no_procesable else {}
    return {
        **exito,
        **VALIDATION_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **CONFLICT_RESPONSE,
        **PAYLOAD_TOO_LARGE_RESPONSE,
        **no_procesable,
        **COMUNES,
    }


def _respuesta(resultado: ResultadoDeAccion | CasoEnviadoAOtrans) -> Resultado:
    if isinstance(resultado, CasoEnviadoAOtrans):
        return CasoEnviadoAOtransResponse.desde_dominio(resultado)
    return ResultadoDeAccionResponse.desde_dominio(resultado)


def build_acciones_router(ejecutar: EjecutarAccion) -> APIRouter:
    router = APIRouter(prefix="/incidencias", tags=["Incidencias"])

    @router.post(
        "/{codigo}/confirmar",
        operation_id="confirmarCategoria",
        response_model=Resultado,
        summary="Confirmar la categoría inicial del clasificador.",
        description=(
            f"{INICIO}Confirma una sola vez la categoría propuesta en un caso clasificado sin revisar. "
            f"No lleva cuerpo.{CIERRE}"
        ),
        responses=_respuestas(AccionIncidencia.CONFIRMAR, con_no_procesable=False),
    )
    async def confirmar_categoria(sesion: CasosDep, codigo: CodigoDep, _cuerpo: CuerpoVacioDep) -> Resultado:
        return _respuesta(await ejecutar.execute(sesion, codigo, Confirmar()))

    @router.post(
        "/{codigo}/corregir",
        operation_id="corregirCategoria",
        response_model=Resultado,
        summary="Corregir la categoría del caso.",
        description=(
            f"{INICIO}Corrige una sola vez, y nunca después de confirmar. Corregir a denuncia-corrupcion es "
            "irreversible para quien lo hace: la base envía el caso a OTRANS y, si sale de su vista, responde "
            "{ codigo, enviadoAOtrans: true }. Cuando OTRANS corrige a queja, reclamo u otro devuelve el caso al "
            f"establecimiento de origen y exige descripcionDerivacion.{CIERRE}"
        ),
        responses=_respuestas(AccionIncidencia.CORREGIR),
    )
    async def corregir_categoria(sesion: CasosDep, codigo: CodigoDep, cuerpo: CorreccionRequest) -> Resultado:
        return _respuesta(await ejecutar.execute(sesion, codigo, cuerpo.a_accion()))

    @router.post(
        "/{codigo}/derivar",
        operation_id="derivarIncidencia",
        response_model=Resultado,
        summary="Derivar el caso a su área receptora.",
        description=(
            f"{INICIO}Una queja, reclamo u otro va solo al área activa del establecimiento de origen; una denuncia "
            "por corrupción permanece en su área OTRANS. areaDestino es opcional y solo confirma ese destino "
            f"vinculado. La descripción es obligatoria.{CIERRE}"
        ),
        responses=_respuestas(AccionIncidencia.DERIVAR),
    )
    async def derivar_incidencia(sesion: CasosDep, codigo: CodigoDep, cuerpo: DerivacionRequest) -> Resultado:
        return _respuesta(await ejecutar.execute(sesion, codigo, cuerpo.a_accion()))

    @router.post(
        "/{codigo}/tomar",
        operation_id="tomarIncidencia",
        response_model=Resultado,
        summary="Tomar el caso en gestión.",
        description=(
            f"{INICIO}Pasa el caso a en-gestion desde clasificado ya revisado o desde derivado. "
            f"No lleva cuerpo.{CIERRE}"
        ),
        responses=_respuestas(AccionIncidencia.TOMAR),
    )
    async def tomar_incidencia(sesion: CasosDep, codigo: CodigoDep, _cuerpo: CuerpoVacioDep) -> Resultado:
        return _respuesta(await ejecutar.execute(sesion, codigo, Tomar()))

    @router.post(
        "/{codigo}/resolver",
        operation_id="resolverIncidencia",
        response_model=Resultado,
        summary="Resolver el caso.",
        description=(
            f"{INICIO}Registra una sola vez las medidas tomadas, el fundamento y el resultado, y deja el caso en "
            f"resuelto.{CIERRE}"
        ),
        responses=_respuestas(AccionIncidencia.RESOLVER),
    )
    async def resolver_incidencia(sesion: CasosDep, codigo: CodigoDep, cuerpo: ResolucionRequest) -> Resultado:
        return _respuesta(await ejecutar.execute(sesion, codigo, cuerpo.a_accion()))

    @router.post(
        "/{codigo}/archivar",
        operation_id="archivarIncidencia",
        response_model=Resultado,
        summary="Archivar el caso a mano.",
        description=(
            f"{INICIO}Archiva desde clasificado, derivado o en-gestion con un motivo manual y su justificación. "
            f"Los motivos VENCIDA_SIN_ATENDER y RESUELTA_VIGENCIA los pone el sistema y aquí responden 400.{CIERRE}"
        ),
        responses=_respuestas(AccionIncidencia.ARCHIVAR),
    )
    async def archivar_incidencia(sesion: CasosDep, codigo: CodigoDep, cuerpo: ArchivoRequest) -> Resultado:
        return _respuesta(await ejecutar.execute(sesion, codigo, cuerpo.a_accion()))

    @router.post(
        "/{codigo}/reabrir",
        operation_id="reabrirIncidencia",
        response_model=Resultado,
        summary="Reabrir un caso archivado.",
        description=(
            f"{INICIO}Devuelve un archivado a en-gestion, tomado por quien reabre y con el motivo. Solo se reabre "
            f"lo archivado por DATOS_INSUFICIENTES, NO_CORRESPONDE o VENCIDA_SIN_ATENDER.{CIERRE}"
        ),
        responses=_respuestas(AccionIncidencia.REABRIR),
    )
    async def reabrir_incidencia(sesion: CasosDep, codigo: CodigoDep, cuerpo: ReaperturaRequest) -> Resultado:
        return _respuesta(await ejecutar.execute(sesion, codigo, cuerpo.a_accion()))

    return router
