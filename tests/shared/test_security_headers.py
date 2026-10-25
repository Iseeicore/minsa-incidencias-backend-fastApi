from http import HTTPStatus

import pytest
from starlette.types import Message, Receive, Scope, Send

from app.shared.security_headers import SecurityHeadersMiddleware
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.fakes import RaisingPlazoRepository
from tests.helpers.vectores import vectores_del_nodo

ORIGEN = "https://app.minsa.gob.pe"
RUTA = "/v1/catalogos/plazos"


class SondaQueFalla:
    async def ping(self) -> bool:
        message = "falla de la sonda"
        raise RuntimeError(message)


CABECERAS_DE_SEGURIDAD = {**vectores_del_nodo()["helmet"], "cache-control": "no-store"}


@pytest.mark.parametrize(
    "ruta", ["/salud", RUTA, "/v1/no-existe", "/no-existe"], ids=["salud", "v1", "v1-404", "raiz-404"]
)
async def test_toda_respuesta_lleva_las_cabeceras_de_seguridad(ruta: str) -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get(ruta)

    for nombre, valor in CABECERAS_DE_SEGURIDAD.items():
        assert respuesta.headers[nombre] == valor


@pytest.mark.parametrize("ruta", ["/salud/listo", RUTA], ids=["raiz", "v1"])
async def test_un_error_inesperado_tambien_lleva_las_cabeceras_de_seguridad_y_de_cors(ruta: str) -> None:
    sonda = SondaQueFalla()
    contenedor = un_contenedor(RaisingPlazoRepository(RuntimeError("boom")), sonda=sonda)
    async with un_cliente(contenedor, cors_origins=(ORIGEN,)) as cliente:
        respuesta = await cliente.get(ruta, headers={"Origin": ORIGEN})

    assert respuesta.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert respuesta.json()["errorCode"] == "INTERNAL_ERROR"
    for nombre, valor in CABECERAS_DE_SEGURIDAD.items():
        assert respuesta.headers[nombre] == valor
    assert respuesta.headers["access-control-allow-origin"] == ORIGEN


async def test_la_peticion_previa_de_cors_tambien_lleva_las_cabeceras_de_seguridad() -> None:
    cabeceras = {"Origin": ORIGEN, "Access-Control-Request-Method": "GET"}
    async with un_cliente(un_contenedor(), cors_origins=(ORIGEN,)) as cliente:
        respuesta = await cliente.options(RUTA, headers=cabeceras)

    assert respuesta.status_code == HTTPStatus.OK
    for nombre, valor in CABECERAS_DE_SEGURIDAD.items():
        assert respuesta.headers[nombre] == valor


@pytest.mark.parametrize("ruta", ["/docs", "/redoc", "/openapi.json"])
async def test_la_documentacion_no_lleva_la_politica_de_contenido(ruta: str) -> None:
    async with un_cliente(un_contenedor(), docs_enabled=True) as cliente:
        respuesta = await cliente.get(ruta)

    assert "content-security-policy" not in respuesta.headers
    assert respuesta.headers["x-content-type-options"] == "nosniff"


async def test_un_alcance_que_no_es_http_pasa_sin_tocar_nada() -> None:
    alcances: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:  # noqa: ARG001
        alcances.append(scope["type"])

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        raise AssertionError(message)

    await SecurityHeadersMiddleware(app)({"type": "lifespan"}, receive, send)

    assert alcances == ["lifespan"]
