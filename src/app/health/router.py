from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.enums.health_status import HealthStatus
from app.shared.http_errors import INTERNAL_RESPONSE, json_example

if TYPE_CHECKING:
    from app.shared.ports import DatabaseProbe


class HealthResponse(BaseModel):
    status: HealthStatus


LIVE_PATH = "/salud"
READY_PATH = "/salud/listo"
LIVE_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {"description": "El proceso está vivo", "content": json_example({"status": HealthStatus.OK})}
}
READY_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {"description": "La base atiende", "content": json_example({"status": HealthStatus.OK})},
    HTTPStatus.SERVICE_UNAVAILABLE: {
        "model": HealthResponse,
        "description": "La base no atiende",
        "content": json_example({"status": HealthStatus.UNAVAILABLE}),
    },
}


def build_health_router(probe: DatabaseProbe) -> APIRouter:
    router = APIRouter(tags=["salud"])

    @router.head(LIVE_PATH, include_in_schema=False)
    @router.get(
        LIVE_PATH,
        response_model=HealthResponse,
        summary="Comprobar que el proceso está vivo",
        description="No consulta la base; la usan el HEALTHCHECK del contenedor y el balanceador.",
        responses={**LIVE_RESPONSE, **INTERNAL_RESPONSE},
    )
    async def live() -> HealthResponse:
        return HealthResponse(status=HealthStatus.OK)

    @router.head(READY_PATH, include_in_schema=False)
    @router.get(
        READY_PATH,
        response_model=HealthResponse,
        summary="Comprobar que el servicio puede atender",
        description="Consulta la base y responde 503 si no atiende.",
        responses={**READY_RESPONSE, **INTERNAL_RESPONSE},
    )
    async def ready() -> JSONResponse:
        available = await probe.ping()
        status = HTTPStatus.OK if available else HTTPStatus.SERVICE_UNAVAILABLE
        body = HealthResponse(status=HealthStatus.OK if available else HealthStatus.UNAVAILABLE)
        return JSONResponse(status_code=status, content=body.model_dump(mode="json"))

    return router
