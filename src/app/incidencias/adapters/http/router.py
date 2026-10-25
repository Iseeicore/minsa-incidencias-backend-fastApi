from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Response

from app.constants.incidencias import CABECERAS_DE_IMAGEN
from app.enums.error_code import ErrorCode
from app.enums.vista_codigo import VistaCodigo
from app.incidencias.adapters.http.ejemplos import CASO_EJEMPLO, DETALLE_EJEMPLO
from app.incidencias.adapters.http.filtros import consulta_de_listado, filtros_de_conteos
from app.incidencias.adapters.http.parametros_de_ruta import codigo_de_incidencia, identificador_de_evidencia
from app.incidencias.adapters.http.schemas import (
    CasoDetalleResponse,
    CasosPorVencerResponse,
    ConteosDeCasosResponse,
    PaginaDeCasosResponse,
)
from app.incidencias.domain.consultas import ConsultaListado, FiltrosConsulta
from app.shared.auth_deps import require_session, require_vista
from app.shared.http_errors import (
    INTERNAL_RESPONSE,
    RATE_LIMITED_RESPONSE,
    SIN_SESION_RESPONSE,
    VALIDATION_RESPONSE,
    error_response,
    json_example,
)
from app.shared.sesion import SesionActual

if TYPE_CHECKING:
    from app.incidencias.application.consultar_incidencia import ConsultarIncidencia
    from app.incidencias.application.contar_incidencias import ContarIncidencias
    from app.incidencias.application.contenido_de_evidencia import ContenidoDeEvidencia
    from app.incidencias.application.incidencias_por_vencer import IncidenciasPorVencer
    from app.incidencias.application.listar_incidencias import ListarIncidencias

FORBIDDEN_RESPONSE = error_response(HTTPStatus.FORBIDDEN, ErrorCode.FORBIDDEN)
NOT_FOUND_RESPONSE = error_response(HTTPStatus.NOT_FOUND, ErrorCode.NOT_FOUND)
EVIDENCIA_NO_DISPONIBLE_RESPONSE = error_response(HTTPStatus.NOT_FOUND, ErrorCode.EVIDENCIA_NO_DISPONIBLE)

CONTEO_EJEMPLO = {"cantidad": 3, "conMas": False}
RESPUESTAS_DE_EXITO: dict[str, dict[int | str, dict[str, object]]] = {
    "pagina": {
        HTTPStatus.OK: {
            "description": "Página de casos.",
            "content": json_example({"items": [CASO_EJEMPLO], "siguiente": None, "hayMas": False}),
        }
    },
    "conteos": {
        HTTPStatus.OK: {
            "description": "Conteos acotados.",
            "content": json_example(
                {
                    "todos": CONTEO_EJEMPLO,
                    "total": CONTEO_EJEMPLO,
                    "porEstado": {
                        "registrado": CONTEO_EJEMPLO,
                        "clasificado": CONTEO_EJEMPLO,
                        "derivado": CONTEO_EJEMPLO,
                        "en-gestion": CONTEO_EJEMPLO,
                        "resuelto": CONTEO_EJEMPLO,
                        "archivado": CONTEO_EJEMPLO,
                    },
                }
            ),
        }
    },
    "por_vencer": {
        HTTPStatus.OK: {
            "description": "Resumen de la campana.",
            "content": json_example({"total": 1, "porVencer": 1, "vencidos": 0, "casos": [CASO_EJEMPLO]}),
        }
    },
    "detalle": {
        HTTPStatus.OK: {"description": "Detalle del caso.", "content": json_example(DETALLE_EJEMPLO)},
    },
    "evidencia": {
        HTTPStatus.OK: {
            "description": "Bytes de la imagen; Content-Type es el tipo guardado en la evidencia (JPEG, PNG o WebP).",
            "content": {"image/jpeg": {}, "image/png": {}, "image/webp": {}},
        }
    },
}

CasosDep = Annotated[SesionActual, Depends(require_vista(VistaCodigo.CASOS))]
SesionDep = Annotated[SesionActual, Depends(require_session)]
ConsultaDep = Annotated[ConsultaListado, Depends(consulta_de_listado)]
FiltrosDep = Annotated[FiltrosConsulta, Depends(filtros_de_conteos)]
CodigoDep = Annotated[str, Depends(codigo_de_incidencia)]
EvidenciaDep = Annotated[str, Depends(identificador_de_evidencia)]


def build_incidencias_router(
    listar: ListarIncidencias,
    contar: ContarIncidencias,
    por_vencer: IncidenciasPorVencer,
    consultar: ConsultarIncidencia,
    evidencia: ContenidoDeEvidencia,
) -> APIRouter:
    router = APIRouter(prefix="/incidencias", tags=["Incidencias"])
    comunes = {**SIN_SESION_RESPONSE, **RATE_LIMITED_RESPONSE, **INTERNAL_RESPONSE}

    @router.get(
        "",
        operation_id="listarIncidencias",
        response_model=PaginaDeCasosResponse,
        summary="Listar los casos que la sesión puede ver.",
        description="Página de casos por cursor, con filtros por estado, categoría, texto, establecimiento y fechas.",
        responses={**RESPUESTAS_DE_EXITO["pagina"], **VALIDATION_RESPONSE, **FORBIDDEN_RESPONSE, **comunes},
    )
    async def listar_incidencias(sesion: CasosDep, consulta: ConsultaDep) -> PaginaDeCasosResponse:
        return PaginaDeCasosResponse.desde_dominio(await listar.execute(sesion, consulta))

    @router.get(
        "/conteos",
        operation_id="contarIncidencias",
        response_model=ConteosDeCasosResponse,
        summary="Contar los casos por estado.",
        description="Conteos acotados al tope de conteo, con los mismos filtros del listado.",
        responses={**RESPUESTAS_DE_EXITO["conteos"], **VALIDATION_RESPONSE, **FORBIDDEN_RESPONSE, **comunes},
    )
    async def contar_incidencias(sesion: CasosDep, filtros: FiltrosDep) -> ConteosDeCasosResponse:
        return ConteosDeCasosResponse.desde_dominio(await contar.execute(sesion, filtros))

    @router.get(
        "/por-vencer",
        operation_id="consultarIncidenciasPorVencer",
        response_model=CasosPorVencerResponse,
        summary="Resumir los casos que vencen pronto.",
        description="Casos abiertos que a la sesión le toca atender y vencen pronto o ya vencieron.",
        responses={**RESPUESTAS_DE_EXITO["por_vencer"], **comunes},
    )
    async def incidencias_por_vencer(sesion: SesionDep) -> CasosPorVencerResponse:
        return CasosPorVencerResponse.desde_dominio(await por_vencer.execute(sesion))

    @router.get(
        "/{codigo}",
        operation_id="obtenerIncidencia",
        response_model=CasoDetalleResponse,
        summary="Obtener el detalle de un caso.",
        description="Detalle del caso con sus evidencias, su historial y las acciones que la sesión puede hacer.",
        responses={**RESPUESTAS_DE_EXITO["detalle"], **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE, **comunes},
    )
    async def obtener_incidencia(sesion: CasosDep, codigo: CodigoDep) -> CasoDetalleResponse:
        return CasoDetalleResponse.desde_dominio(await consultar.execute(sesion, codigo))

    @router.get(
        "/{codigo}/evidencias/{evidenciaId}/contenido",  # noqa: FAST003
        operation_id="obtenerContenidoDeEvidencia",
        summary="Obtener la imagen de una evidencia.",
        description="Entrega los bytes de la imagen guardada como data URI base64 canónico.",
        response_class=Response,
        responses={**RESPUESTAS_DE_EXITO["evidencia"], **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE, **comunes},
    )
    async def contenido_de_evidencia(sesion: CasosDep, codigo: CodigoDep, evidencia_id: EvidenciaDep) -> Response:
        imagen = await evidencia.execute(sesion, codigo, evidencia_id)
        cabeceras = {**CABECERAS_DE_IMAGEN, "Content-Length": str(len(imagen.contenido))}
        return Response(content=imagen.contenido, media_type=imagen.tipo, headers=cabeceras)

    return router
