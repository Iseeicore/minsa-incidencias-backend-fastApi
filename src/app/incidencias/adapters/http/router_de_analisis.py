from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

from app.enums.rol_codigo import RolCodigo
from app.enums.vista_codigo import VistaCodigo
from app.incidencias.adapters.http.ejemplos import ANALISIS_EJEMPLO
from app.incidencias.adapters.http.parametros_de_ruta import codigo_de_incidencia
from app.incidencias.adapters.http.router import FORBIDDEN_RESPONSE, NOT_FOUND_RESPONSE
from app.incidencias.adapters.http.schemas_de_analisis import AnalisisIaResponse
from app.shared.auth_deps import require_vista_y_rol
from app.shared.http_errors import (
    INTERNAL_RESPONSE,
    RATE_LIMITED_RESPONSE,
    SIN_SESION_RESPONSE,
    json_example,
)
from app.shared.sesion import SesionActual

if TYPE_CHECKING:
    from app.incidencias.application.consultar_analisis import ConsultarAnalisis

RUTA_CLASIFICACION = "/{codigo}/clasificacion"
RUTA_ALIAS = "/{codigo}/analisis-ia"
RESUMEN = "Consultar el análisis de clasificación guardado de un caso."
DETALLE = (
    "Exige la vista CASOS y el rol OTRANS o ADMINISTRADOR. Busca el caso con la visibilidad de la sesión y lee el "
    "análisis que guardó el clasificador: explicación, señales, supuestos y procedimiento normativo, requisitos "
    "faltantes, ficha de derivación y datos mencionados. Solo lee: no vuelve a clasificar ni llama a un modelo."
)
ANALISIS_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {"description": "Análisis guardado.", "content": json_example(ANALISIS_EJEMPLO)}
}
ACCESO_AL_ANALISIS = Depends(require_vista_y_rol(VistaCodigo.CASOS, RolCodigo.OTRANS, RolCodigo.ADMINISTRADOR))
CodigoDep = Annotated[str, Depends(codigo_de_incidencia)]
SupervisorDep = Annotated[SesionActual, ACCESO_AL_ANALISIS]


def build_analisis_router(consultar: ConsultarAnalisis) -> APIRouter:
    router = APIRouter(prefix="/incidencias", tags=["Análisis de clasificación"])
    respuestas = {
        **ANALISIS_RESPONSE,
        **SIN_SESION_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **RATE_LIMITED_RESPONSE,
        **INTERNAL_RESPONSE,
    }

    @router.get(
        RUTA_CLASIFICACION,
        operation_id="obtenerClasificacion",
        response_model=AnalisisIaResponse,
        summary=RESUMEN,
        description=DETALLE,
        responses=respuestas,
    )
    async def obtener_clasificacion(sesion: SupervisorDep, codigo: CodigoDep) -> AnalisisIaResponse:
        return AnalisisIaResponse.desde_dominio(await consultar.execute(sesion, codigo))

    @router.get(
        RUTA_ALIAS,
        operation_id="obtenerAnalisisIa",
        response_model=AnalisisIaResponse,
        summary=RESUMEN,
        description=f"Alias compatible de /incidencias/{{codigo}}/clasificacion. {DETALLE}",
        responses=respuestas,
    )
    async def obtener_analisis_ia(sesion: SupervisorDep, codigo: CodigoDep) -> AnalisisIaResponse:
        return AnalisisIaResponse.desde_dominio(await consultar.execute(sesion, codigo))

    return router
