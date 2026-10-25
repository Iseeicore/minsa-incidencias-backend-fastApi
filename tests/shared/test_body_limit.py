from collections.abc import AsyncIterator
from http import HTTPStatus

from tests.helpers.app_factory import un_cliente, un_contenedor

LIMITE_EN_BYTES = 100 * 1024
CABECERAS_JSON = {"content-type": "application/json"}


def _cuerpo_de(tamano: int) -> bytes:
    return b'{"titulo": "T", "contenido": "' + b"x" * tamano + b'"}'


async def _en_trozos(tamano: int) -> AsyncIterator[bytes]:
    cuerpo = _cuerpo_de(tamano)
    for inicio in range(0, len(cuerpo), 4096):
        yield cuerpo[inicio : inicio + 4096]


async def test_un_cuerpo_declarado_mas_grande_que_el_limite_responde_413_con_el_formato_unico() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.post("/v1/notas", content=_cuerpo_de(LIMITE_EN_BYTES), headers=CABECERAS_JSON)

    assert respuesta.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert respuesta.json()["errorCode"] == "PAYLOAD_TOO_LARGE"
    assert respuesta.json()["path"] == "/v1/notas"


async def test_un_cuerpo_en_trozos_que_pasa_el_limite_responde_413() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.post("/v1/notas", content=_en_trozos(LIMITE_EN_BYTES), headers=CABECERAS_JSON)

    assert respuesta.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert respuesta.json()["errorCode"] == "PAYLOAD_TOO_LARGE"


async def test_un_cuerpo_dentro_del_limite_llega_a_la_validacion_de_la_ruta() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.post("/v1/notas", content=_cuerpo_de(20_000), headers=CABECERAS_JSON)

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert respuesta.json()["errorCode"] == "REQUEST_INVALID"
