from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query

from app.constants.indicadores import PERIODO_POR_DEFECTO
from app.enums.error_code import ErrorCode
from app.enums.periodo_indicadores import PeriodoIndicadores
from app.enums.vista_codigo import VistaCodigo
from app.incidencias.adapters.http.ejemplos import INDICADORES_EJEMPLO
from app.incidencias.adapters.http.schemas_de_indicadores import IndicadoresResponse
from app.shared.auth_deps import require_vista
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
    from app.incidencias.application.obtener_indicadores import ObtenerIndicadores

FORBIDDEN_RESPONSE = error_response(HTTPStatus.FORBIDDEN, ErrorCode.FORBIDDEN)
INDICADORES_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {"description": "Indicadores del periodo.", "content": json_example(INDICADORES_EJEMPLO)}
}
InicioDep = Annotated[SesionActual, Depends(require_vista(VistaCodigo.INICIO))]


def build_indicadores_router(indicadores: ObtenerIndicadores) -> APIRouter:
    router = APIRouter(prefix="/indicadores", tags=["Indicadores"])

    @router.get(
        "",
        operation_id="obtenerIndicadores",
        response_model=IndicadoresResponse,
        summary="Obtener los indicadores del tablero de inicio.",
        description=(
            f"Resume los casos visibles para la sesión en el periodo pedido ({PERIODO_POR_DEFECTO} por defecto). "
            "Exige la vista inicio. Las tarjetas dependen de los roles y solo recibidos, resueltos y corregidas a "
            "corrupción traen el valor del periodo anterior. porCategoria omite las categorías sin casos e incluye "
            "sin-categoria solo para roles que ven casos sin categoría. La evolución se agrupa por día, o por semana "
            "en 90d. El alcance es TODO para roles que cuentan todas las áreas y AREA para el resto."
        ),
        responses={
            **INDICADORES_RESPONSE,
            **VALIDATION_RESPONSE,
            **SIN_SESION_RESPONSE,
            **FORBIDDEN_RESPONSE,
            **RATE_LIMITED_RESPONSE,
            **INTERNAL_RESPONSE,
        },
    )
    async def obtener_indicadores(
        sesion: InicioDep, periodo: Annotated[PeriodoIndicadores, Query()] = PERIODO_POR_DEFECTO
    ) -> IndicadoresResponse:
        return IndicadoresResponse.desde_dominio(await indicadores.execute(sesion, periodo))

    return router
