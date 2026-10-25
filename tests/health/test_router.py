from http import HTTPStatus

import pytest

from tests.helpers.app_factory import un_cliente, un_contenedor


async def test_salud_responde_sin_consultar_la_base() -> None:
    async with un_cliente(un_contenedor(base_disponible=False)) as cliente:
        respuesta = await cliente.get("/salud")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == {"status": "ok"}


async def test_listo_responde_200_si_la_base_atiende() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get("/salud/listo")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == {"status": "ok"}


async def test_listo_responde_503_si_la_base_no_atiende() -> None:
    async with un_cliente(un_contenedor(base_disponible=False)) as cliente:
        respuesta = await cliente.get("/salud/listo")

    assert respuesta.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert respuesta.json() == {"status": "unavailable"}


@pytest.mark.parametrize(
    ("ruta", "base_disponible", "estado"),
    [
        ("/salud", True, HTTPStatus.OK),
        ("/salud", False, HTTPStatus.OK),
        ("/salud/listo", True, HTTPStatus.OK),
        ("/salud/listo", False, HTTPStatus.SERVICE_UNAVAILABLE),
    ],
    ids=["vivo", "vivo-sin-base", "listo", "no-listo"],
)
async def test_head_responde_con_el_mismo_estado_que_get_y_sin_cuerpo(
    ruta: str,
    base_disponible: bool,  # noqa: FBT001
    estado: HTTPStatus,
) -> None:
    async with un_cliente(un_contenedor(base_disponible=base_disponible)) as cliente:
        respuesta = await cliente.head(ruta)

    assert respuesta.status_code == estado
    assert respuesta.content == b""
