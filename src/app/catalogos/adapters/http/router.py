from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from app.catalogos.adapters.http.schemas import PlazosDeCategoriasResponse
from app.shared.auth_deps import require_session
from app.shared.http_errors import (
    INTERNAL_RESPONSE,
    RATE_LIMITED_RESPONSE,
    SIN_SESION_RESPONSE,
    json_example,
)

if TYPE_CHECKING:
    from app.catalogos.application.listar_plazos import ListarPlazos

PLAZOS_EJEMPLO = {
    "items": [
        {"categoria": "denuncia-corrupcion", "plazoDiasHabiles": 3, "archivaPorVencimiento": False},
        {"categoria": "reclamo", "plazoDiasHabiles": 30, "archivaPorVencimiento": True},
    ]
}
PLAZOS_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {"description": "Plazos por categoría.", "content": json_example(PLAZOS_EJEMPLO)}
}


def build_catalogos_router(listar_plazos: ListarPlazos) -> APIRouter:
    router = APIRouter(prefix="/catalogos", tags=["Catálogos"], dependencies=[Depends(require_session)])

    @router.get(
        "/plazos",
        operation_id="listarPlazosPorCategoria",
        response_model=PlazosDeCategoriasResponse,
        summary="Listar el plazo de atención de cada categoría.",
        description=(
            "Devuelve, para cada categoría activa, su plazo en días hábiles y si el caso se archiva "
            "automáticamente al vencer. Solo exige sesión; no depende del rol."
        ),
        responses={
            **PLAZOS_RESPONSE,
            **SIN_SESION_RESPONSE,
            **RATE_LIMITED_RESPONSE,
            **INTERNAL_RESPONSE,
        },
    )
    async def plazos() -> PlazosDeCategoriasResponse:
        return PlazosDeCategoriasResponse.desde_dominio(await listar_plazos.execute())

    return router
