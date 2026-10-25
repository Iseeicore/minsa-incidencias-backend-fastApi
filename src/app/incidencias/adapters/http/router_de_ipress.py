from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.constants.incidencias import CABECERAS_DE_IMAGEN
from app.constants.indicadores import PERIODO_POR_DEFECTO
from app.enums.periodo_indicadores import PeriodoIndicadores
from app.enums.rol_codigo import RolCodigo
from app.enums.vista_codigo import VistaCodigo
from app.incidencias.adapters.http.ejemplos import (
    CASO_EJEMPLO,
    DETALLE_EJEMPLO,
    INDICADORES_EJEMPLO,
    IPRESS_EJEMPLO,
    RESUMEN_DE_IPRESS_EJEMPLO,
)
from app.incidencias.adapters.http.filtros import consulta_de_listado_de_ipress as consulta_de_listado
from app.incidencias.adapters.http.filtros import filtros_de_conteos
from app.incidencias.adapters.http.filtros_de_ipress import consulta_de_ipress
from app.incidencias.adapters.http.parametros_de_ruta import (
    codigo_de_incidencia,
    identificador_de_evidencia,
    renipress_de_ruta,
)
from app.incidencias.adapters.http.router import FORBIDDEN_RESPONSE, NOT_FOUND_RESPONSE, RESPUESTAS_DE_EXITO
from app.incidencias.adapters.http.schemas import (
    CasoDetalleResponse,
    ConteosDeCasosResponse,
    PaginaDeCasosResponse,
)
from app.incidencias.adapters.http.schemas_de_indicadores import IndicadoresResponse, ResumenDeIpressResponse
from app.incidencias.adapters.http.schemas_de_ipress import PaginaDeIpressResponse
from app.incidencias.domain.consultas import ConsultaListado, FiltrosConsulta
from app.incidencias.domain.ipress import ConsultaDeIpress
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
    from app.incidencias.application.consulta_de_ipress import (
        ConsultarIncidenciaDeIpress,
        ContarIncidenciasDeIpress,
        ContenidoDeEvidenciaDeIpress,
        ListarIncidenciasDeIpress,
        ObtenerIndicadoresDeIpress,
        ObtenerResumenDeIpress,
    )
    from app.incidencias.application.listar_ipress import ListarIpress

ACCESO = (
    "Exige la vista consulta-ipress y el rol OTRANS o ADMINISTRADOR. Es un acceso supervisor de solo lectura, "
    "independiente del alcance operativo de la bandeja."
)
ACOTADO = (
    "Los casos se acotan al establecimiento de origen, aunque su destino sea otra área, "
    "y salen sin acciones de gestión."
)
RESPUESTAS_DE_IPRESS: dict[str, dict[int | str, dict[str, object]]] = {
    "establecimientos": {
        HTTPStatus.OK: {
            "description": "Página de IPRESS.",
            "content": json_example({"items": [IPRESS_EJEMPLO], "siguiente": None, "hayMas": False}),
        }
    },
    "indicadores": {
        HTTPStatus.OK: {"description": "Indicadores de la IPRESS.", "content": json_example(INDICADORES_EJEMPLO)}
    },
    "resumen": {
        HTTPStatus.OK: {"description": "Resumen de la IPRESS.", "content": json_example(RESUMEN_DE_IPRESS_EJEMPLO)}
    },
    "pagina": {
        HTTPStatus.OK: {
            "description": "Página de casos.",
            "content": json_example({"items": [{**CASO_EJEMPLO, "acciones": []}], "siguiente": None, "hayMas": False}),
        }
    },
    "detalle": {
        HTTPStatus.OK: {
            "description": "Detalle del caso.",
            "content": json_example({**DETALLE_EJEMPLO, "acciones": []}),
        }
    },
}

ACCESO_A_IPRESS = Depends(require_vista_y_rol(VistaCodigo.CONSULTA_IPRESS, RolCodigo.OTRANS, RolCodigo.ADMINISTRADOR))
SupervisorDep = Annotated[SesionActual, ACCESO_A_IPRESS]
ConsultaDep = Annotated[ConsultaListado, Depends(consulta_de_listado)]
FiltrosDep = Annotated[FiltrosConsulta, Depends(filtros_de_conteos)]
EstablecimientosDep = Annotated[ConsultaDeIpress, Depends(consulta_de_ipress)]
CodigoDep = Annotated[str, Depends(codigo_de_incidencia)]
EvidenciaDep = Annotated[str, Depends(identificador_de_evidencia)]
PeriodoDep = Annotated[PeriodoIndicadores, Query()]


def build_ipress_router(  # noqa: PLR0913, PLR0917
    establecimientos: ListarIpress,
    resumen: ObtenerResumenDeIpress,
    indicadores: ObtenerIndicadoresDeIpress,
    listar: ListarIncidenciasDeIpress,
    contar: ContarIncidenciasDeIpress,
    consultar: ConsultarIncidenciaDeIpress,
    evidencia: ContenidoDeEvidenciaDeIpress,
) -> APIRouter:
    router = APIRouter(prefix="/consulta-ipress", tags=["Consulta de IPRESS"], dependencies=[ACCESO_A_IPRESS])
    comunes = {**SIN_SESION_RESPONSE, **FORBIDDEN_RESPONSE, **RATE_LIMITED_RESPONSE, **INTERNAL_RESPONSE}
    de_ipress = {**NOT_FOUND_RESPONSE, **comunes}

    @router.get(
        "/establecimientos",
        operation_id="buscarIpress",
        response_model=PaginaDeIpressResponse,
        summary="Buscar IPRESS activas.",
        description=f"{ACCESO} Mismo formato y cursor que /areas, restringido a establecimientos activos.",
        responses={**RESPUESTAS_DE_IPRESS["establecimientos"], **VALIDATION_RESPONSE, **comunes},
    )
    async def buscar_ipress(consulta: EstablecimientosDep) -> PaginaDeIpressResponse:
        return PaginaDeIpressResponse.desde_dominio(await establecimientos.execute(consulta))

    @router.get(
        "/{renipress}/indicadores",
        operation_id="obtenerIndicadoresDeIpress",
        response_model=IndicadoresResponse,
        summary="Obtener los indicadores de una IPRESS.",
        description=(
            f"{ACCESO} Calcula los indicadores del tablero solo con los casos originados en esa IPRESS; "
            "el alcance es AREA."
        ),
        responses={**RESPUESTAS_DE_IPRESS["indicadores"], **VALIDATION_RESPONSE, **de_ipress},
    )
    async def obtener_indicadores_de_ipress(
        sesion: SupervisorDep, renipress: str, periodo: PeriodoDep = PERIODO_POR_DEFECTO
    ) -> IndicadoresResponse:
        return IndicadoresResponse.desde_dominio(
            await indicadores.execute(sesion, renipress_de_ruta(renipress), periodo)
        )

    @router.get(
        "/{renipress}/resumen",
        operation_id="obtenerResumenDeIpress",
        response_model=ResumenDeIpressResponse,
        summary="Obtener los conteos generales de una IPRESS.",
        description=(
            f"{ACCESO} Cuenta todo el historial de la IPRESS, sin filtros: total, abiertos, en gestión, resueltos, "
            "archivados y categorías."
        ),
        responses={**RESPUESTAS_DE_IPRESS["resumen"], **de_ipress},
    )
    async def obtener_resumen_de_ipress(renipress: str) -> ResumenDeIpressResponse:
        return ResumenDeIpressResponse.desde_dominio(await resumen.execute(renipress_de_ruta(renipress)))

    @router.get(
        "/{renipress}/incidencias",
        operation_id="listarIncidenciasDeIpress",
        response_model=PaginaDeCasosResponse,
        summary="Listar los casos originados en una IPRESS.",
        description=f"{ACCESO} Usa los filtros, validaciones y cursores de la bandeja operativa. {ACOTADO}",
        responses={**RESPUESTAS_DE_IPRESS["pagina"], **VALIDATION_RESPONSE, **de_ipress},
    )
    async def listar_incidencias_de_ipress(
        sesion: SupervisorDep, renipress: str, consulta: ConsultaDep
    ) -> PaginaDeCasosResponse:
        pagina = await listar.execute(sesion, renipress_de_ruta(renipress), consulta)
        return PaginaDeCasosResponse.desde_dominio(pagina)

    @router.get(
        "/{renipress}/conteos",
        operation_id="contarIncidenciasDeIpress",
        response_model=ConteosDeCasosResponse,
        summary="Contar por estado los casos originados en una IPRESS.",
        description=f"{ACCESO} Mismos filtros y reglas de conteo acotado que /incidencias/conteos. {ACOTADO}",
        responses={**RESPUESTAS_DE_EXITO["conteos"], **VALIDATION_RESPONSE, **de_ipress},
    )
    async def contar_incidencias_de_ipress(
        sesion: SupervisorDep, renipress: str, filtros: FiltrosDep
    ) -> ConteosDeCasosResponse:
        conteos = await contar.execute(sesion, renipress_de_ruta(renipress), filtros)
        return ConteosDeCasosResponse.desde_dominio(conteos)

    @router.get(
        "/{renipress}/incidencias/{codigo}",
        operation_id="obtenerIncidenciaDeIpress",
        response_model=CasoDetalleResponse,
        summary="Obtener el detalle de un caso de una IPRESS.",
        description=f"{ACCESO} Detalle e historial de un caso originado en esa IPRESS. {ACOTADO}",
        responses={**RESPUESTAS_DE_IPRESS["detalle"], **de_ipress},
    )
    async def obtener_incidencia_de_ipress(
        sesion: SupervisorDep, renipress: str, codigo: CodigoDep
    ) -> CasoDetalleResponse:
        return CasoDetalleResponse.desde_dominio(await consultar.execute(sesion, renipress_de_ruta(renipress), codigo))

    @router.get(
        "/{renipress}/incidencias/{codigo}/evidencias/{evidenciaId}/contenido",  # noqa: FAST003
        operation_id="obtenerContenidoDeEvidenciaDeIpress",
        summary="Obtener la imagen de una evidencia de un caso de una IPRESS.",
        description=f"{ACCESO} Mismas restricciones y cabeceras que la lectura operativa, con el alcance de la IPRESS.",
        response_class=Response,
        responses={**RESPUESTAS_DE_EXITO["evidencia"], **de_ipress},
    )
    async def contenido_de_evidencia_de_ipress(
        sesion: SupervisorDep, renipress: str, codigo: CodigoDep, evidencia_id: EvidenciaDep
    ) -> Response:
        imagen = await evidencia.execute(sesion, renipress_de_ruta(renipress), codigo, evidencia_id)
        cabeceras = {**CABECERAS_DE_IMAGEN, "Content-Length": str(len(imagen.contenido))}
        return Response(content=imagen.contenido, media_type=imagen.tipo, headers=cabeceras)

    return router
