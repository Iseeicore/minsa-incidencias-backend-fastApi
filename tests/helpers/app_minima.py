from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, ConfigDict
from starlette.types import ASGIApp

from app.constants.limits import JSON_BODY_LIMIT_BYTES
from app.shared.body_limit import BodyLimitMiddleware
from app.shared.http_errors import register_error_handlers
from tests.helpers.fakes import FixedClock


class CuerpoDeEco(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str


def una_app_minima() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app, FixedClock())
    app.add_middleware(BodyLimitMiddleware, max_bytes=JSON_BODY_LIMIT_BYTES)

    @app.post("/eco")
    async def eco(cuerpo: CuerpoDeEco) -> dict[str, str]:
        return {"texto": cuerpo.texto}

    return app


def un_cliente_de(app: ASGIApp) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://prueba")
