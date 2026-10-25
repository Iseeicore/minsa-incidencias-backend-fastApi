from collections.abc import AsyncIterator
from http import HTTPStatus

from starlette.types import Message, Receive, Scope, Send

from app.composition import create_app
from app.shared.body_limit import BodyLimitMiddleware
from tests.helpers.app_factory import un_contenedor
from tests.helpers.app_minima import un_cliente_de, una_app_minima

LIMITE_EN_BYTES = 100 * 1024
CABECERAS_JSON = {"content-type": "application/json"}


def _cuerpo_de(tamano: int) -> bytes:
    return b'{"texto": "' + b"x" * tamano + b'"}'


async def _en_trozos(tamano: int) -> AsyncIterator[bytes]:
    cuerpo = _cuerpo_de(tamano)
    for inicio in range(0, len(cuerpo), 4096):
        yield cuerpo[inicio : inicio + 4096]


async def test_un_cuerpo_declarado_mas_grande_que_el_limite_responde_413_con_el_formato_unico() -> None:
    async with un_cliente_de(una_app_minima()) as cliente:
        respuesta = await cliente.post("/eco", content=_cuerpo_de(LIMITE_EN_BYTES), headers=CABECERAS_JSON)

    assert respuesta.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert respuesta.json()["errorCode"] == "PAYLOAD_TOO_LARGE"
    assert respuesta.json()["path"] == "/eco"


async def test_un_cuerpo_en_trozos_que_pasa_el_limite_responde_413() -> None:
    async with un_cliente_de(una_app_minima()) as cliente:
        respuesta = await cliente.post("/eco", content=_en_trozos(LIMITE_EN_BYTES), headers=CABECERAS_JSON)

    assert respuesta.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert respuesta.json()["errorCode"] == "PAYLOAD_TOO_LARGE"


async def test_un_cuerpo_dentro_del_limite_llega_a_la_ruta() -> None:
    async with un_cliente_de(una_app_minima()) as cliente:
        respuesta = await cliente.post("/eco", content=_cuerpo_de(20_000), headers=CABECERAS_JSON)

    assert respuesta.status_code == HTTPStatus.OK
    assert len(respuesta.json()["texto"]) == 20_000


def test_la_aplicacion_real_monta_el_limite_de_cuerpo() -> None:
    app = create_app(un_contenedor())

    assert any(
        isinstance(middleware.cls, type) and issubclass(middleware.cls, BodyLimitMiddleware)
        for middleware in app.user_middleware
    )


async def test_un_alcance_que_no_es_http_pasa_sin_tocar_nada() -> None:
    alcances: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:  # noqa: ARG001
        alcances.append(scope["type"])

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        raise AssertionError(message)

    await BodyLimitMiddleware(app, max_bytes=10)({"type": "lifespan"}, receive, send)

    assert alcances == ["lifespan"]


async def test_un_mensaje_que_no_es_de_cuerpo_no_cuenta_para_el_limite() -> None:
    recibidos: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:  # noqa: ARG001
        recibidos.append((await receive())["type"])

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        raise AssertionError(message)

    await BodyLimitMiddleware(app, max_bytes=10)({"type": "http", "headers": []}, receive, send)

    assert recibidos == ["http.disconnect"]
