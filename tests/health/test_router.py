from http import HTTPStatus

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
