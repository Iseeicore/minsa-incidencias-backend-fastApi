from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Response

from app.constants.incidencias import CABECERAS_DE_IMAGEN
from app.enums.rol_codigo import RolCodigo
from app.enums.vista_codigo import VistaCodigo
from app.incidencias.adapters.http.ejemplos import DERIVACION_EJEMPLO, DETALLE_EJEMPLO
from app.incidencias.adapters.http.filtros_de_derivacion import (
    consulta_de_derivaciones,
    filtros_de_conteos_de_derivacion,
)
from app.incidencias.adapters.http.parametros_de_ruta import codigo_de_incidencia, identificador_de_evidencia
from app.incidencias.adapters.http.router import FORBIDDEN_RESPONSE, NOT_FOUND_RESPONSE, RESPUESTAS_DE_EXITO
from app.incidencias.adapters.http.schemas_de_derivacion import (
    ConteosDeDerivacionesResponse,
    DerivacionDetalleResponse,
    PaginaDeDerivacionesResponse,
)
from app.incidencias.domain.derivaciones import ConsultaDeDerivaciones, FiltrosDeDerivaciones
from app.shared.auth_deps import require_vista_y_rol
from app.shared.http_errors import (
    INTERNAL_RESPONSE,
    RATE_LIMITED_RESPONSE,
    SIN_SESION_RESPONSE,
    VALIDATION_RESPONSE,
    json_example,
)
from app.shared.sesion import SesionActual

if TYPE_CHECKING:
    from app.incidencias.application.consultar_derivacion import ConsultarDerivacion
    from app.incidencias.application.contar_derivaciones import ContarDerivaciones
    from app.incidencias.application.contenido_de_evidencia_derivada import ContenidoDeEvidenciaDerivada
    from app.incidencias.application.listar_derivaciones import ListarDerivaciones

ACCESO = "Exige la vista derivaciones y el rol OTRANS o ADMINISTRADOR."
CONTEOS_EJEMPLO = {"todos": 4, "pendientes": 1, "enGestion": 1, "resueltos": 1, "archivados": 1}
RESPUESTAS_DE_DERIVACIONES: dict[str, dict[int | str, dict[str, object]]] = {
    "pagina": {
        HTTPStatus.OK: {
            "description": "Página de derivaciones.",
            "content": json_example({"items": [DERIVACION_EJEMPLO], "siguiente": None, "hayMas": False}),
        }
    },
    "conteos": {HTTPStatus.OK: {"description": "Conteos por situación.", "content": json_example(CONTEOS_EJEMPLO)}},
    "detalle": {
        HTTPStatus.OK: {
            "description": "Derivación y caso.",
            "content": json_example({"derivacion": DERIVACION_EJEMPLO, "caso": {**DETALLE_EJEMPLO, "acciones": []}}),
        }
    },
}

ACCESO_A_DERIVACIONES = Depends(
    require_vista_y_rol(VistaCodigo.DERIVACIONES, RolCodigo.OTRANS, RolCodigo.ADMINISTRADOR)
)
DerivacionesDep = Annotated[SesionActual, ACCESO_A_DERIVACIONES]
ConsultaDep = Annotated[ConsultaDeDerivaciones, Depends(consulta_de_derivaciones)]
FiltrosDep = Annotated[FiltrosDeDerivaciones, Depends(filtros_de_conteos_de_derivacion)]
CodigoDep = Annotated[str, Depends(codigo_de_incidencia)]
EvidenciaDep = Annotated[str, Depends(identificador_de_evidencia)]


def build_derivaciones_router(
    listar: ListarDerivaciones,
    contar: ContarDerivaciones,
    consultar: ConsultarDerivacion,
    evidencia: ContenidoDeEvidenciaDerivada,
) -> APIRouter:
    router = APIRouter(prefix="/derivaciones", tags=["Derivaciones"], dependencies=[ACCESO_A_DERIVACIONES])
    comunes = {**SIN_SESION_RESPONSE, **FORBIDDEN_RESPONSE, **RATE_LIMITED_RESPONSE, **INTERNAL_RESPONSE}

    @router.get(
        "",
        operation_id="listarDerivaciones",
        response_model=PaginaDeDerivacionesResponse,
        summary="Listar el seguimiento de casos que OTRANS envió a establecimientos.",
        description=(
            f"{ACCESO} Una fila por caso: su último envío humano desde un área OTRANS a un establecimiento, "
            "ordenada por fecha del envío descendente y paginada por cursor. Los filtros se aplican después de "
            "elegir el último envío. Solo lee; no cambia casos."
        ),
        responses={**RESPUESTAS_DE_DERIVACIONES["pagina"], **VALIDATION_RESPONSE, **comunes},
    )
    async def listar_derivaciones(consulta: ConsultaDep) -> PaginaDeDerivacionesResponse:
        return PaginaDeDerivacionesResponse.desde_dominio(await listar.execute(consulta))

    @router.get(
        "/conteos",
        operation_id="contarDerivaciones",
        response_model=ConteosDeDerivacionesResponse,
        summary="Contar las derivaciones por situación.",
        description=(
            f"{ACCESO} Aplica los mismos filtros que el listado salvo situación, límite y cursor. Pendientes son "
            "los enviados que siguen registrados, clasificados o derivados; archivados se cuentan aparte aunque "
            "antes se hubieran resuelto."
        ),
        responses={**RESPUESTAS_DE_DERIVACIONES["conteos"], **VALIDATION_RESPONSE, **comunes},
    )
    async def contar_derivaciones(filtros: FiltrosDep) -> ConteosDeDerivacionesResponse:
        return ConteosDeDerivacionesResponse.desde_dominio(await contar.execute(filtros))

    @router.get(
        "/{codigo}",
        operation_id="obtenerDerivacion",
        response_model=DerivacionDetalleResponse,
        summary="Obtener el último envío de un caso y su detalle.",
        description=(
            f"{ACCESO} Devuelve el último envío y el detalle e historial reales del caso, sin acciones de gestión."
        ),
        responses={**RESPUESTAS_DE_DERIVACIONES["detalle"], **NOT_FOUND_RESPONSE, **comunes},
    )
    async def obtener_derivacion(sesion: DerivacionesDep, codigo: CodigoDep) -> DerivacionDetalleResponse:
        return DerivacionDetalleResponse.desde_dominio(await consultar.execute(sesion, codigo))

    @router.get(
        "/{codigo}/evidencias/{evidenciaId}/contenido",  # noqa: FAST003
        operation_id="obtenerContenidoDeEvidenciaDerivada",
        summary="Obtener la imagen de una evidencia de un caso derivado.",
        description=(
            f"{ACCESO} Usa el mismo alcance histórico del seguimiento y las mismas restricciones y cabeceras que "
            "el visor operativo."
        ),
        response_class=Response,
        responses={**RESPUESTAS_DE_EXITO["evidencia"], **NOT_FOUND_RESPONSE, **comunes},
    )
    async def contenido_de_evidencia_derivada(
        sesion: DerivacionesDep, codigo: CodigoDep, evidencia_id: EvidenciaDep
    ) -> Response:
        imagen = await evidencia.execute(sesion, codigo, evidencia_id)
        cabeceras = {**CABECERAS_DE_IMAGEN, "Content-Length": str(len(imagen.contenido))}
        return Response(content=imagen.contenido, media_type=imagen.tipo, headers=cabeceras)

    return router
