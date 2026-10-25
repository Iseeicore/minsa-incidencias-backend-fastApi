from http import HTTPStatus

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.shared.csrf import CsrfMiddleware
from tests.helpers.fakes import FixedClock

PERMITIDO = "https://app.minsa.gob.pe"
AJENO = "https://sitio.malicioso.example"


def _cliente() -> AsyncClient:
    app = FastAPI()

    @app.get("/ping")
    @app.post("/ping")
    @app.delete("/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(CsrfMiddleware, allowed_origins=[PERMITIDO], clock=FixedClock())
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://prueba")


@pytest.mark.parametrize("metodo", ["POST", "DELETE"])
async def test_una_escritura_desde_un_origen_ajeno_responde_403(metodo: str) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.request(metodo, "/ping", headers={"Origin": AJENO})

    assert respuesta.status_code == HTTPStatus.FORBIDDEN
    assert respuesta.json() == {
        "success": False,
        "statusCode": 403,
        "errorCode": "FORBIDDEN",
        "message": "No tienes permisos para esta acción.",
        "timestamp": "2026-10-24T12:00:00.000Z",
        "path": "/ping",
    }


@pytest.mark.parametrize("cabeceras", [{"Origin": PERMITIDO}, {}], ids=["origen-permitido", "sin-origen"])
async def test_una_escritura_permitida_o_sin_origen_pasa(cabeceras: dict[str, str]) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post("/ping", headers=cabeceras)

    assert respuesta.status_code == HTTPStatus.OK


async def test_una_lectura_desde_cualquier_origen_pasa() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get("/ping", headers={"Origin": AJENO})

    assert respuesta.status_code == HTTPStatus.OK
