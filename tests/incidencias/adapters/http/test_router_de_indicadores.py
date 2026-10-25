from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.shared.sesion import SesionActual
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import una_sesion
from tests.helpers.indicadores_en_memoria import IndicadoresEnMemoria

RUTA = "/v1/indicadores"
GESTOR = una_sesion(roles=("GESTOR",))


def _cliente(
    lector: IndicadoresEnMemoria | None = None, sesion: SesionActual = GESTOR, *, con_sesion: bool = True
) -> AsyncClient:
    contenedor = un_contenedor(indicadores=lector or IndicadoresEnMemoria())
    return un_cliente(contenedor, con_sesion=con_sesion, sesion=sesion)


async def test_devuelve_los_indicadores_del_periodo_por_defecto() -> None:
    lector = IndicadoresEnMemoria()
    async with _cliente(lector) as cliente:
        respuesta = await cliente.get(RUTA)

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert cuerpo["periodo"] == "7d"
    assert [tarjeta["codigo"] for tarjeta in cuerpo["tarjetas"]] == [
        "recibidos",
        "pendientes",
        "en-gestion",
        "resueltos",
    ]
    assert lector.llamadas[0][1][1] == 7


@pytest.mark.parametrize(("periodo", "dias"), [("7d", 7), ("30d", 30), ("90d", 90)])
async def test_el_periodo_pedido_fija_los_dias_consultados(periodo: str, dias: int) -> None:
    lector = IndicadoresEnMemoria()
    async with _cliente(lector) as cliente:
        respuesta = await cliente.get(RUTA, params={"periodo": periodo})

    assert respuesta.json()["periodo"] == periodo
    assert lector.llamadas[0][1][1] == dias


async def test_un_periodo_desconocido_responde_400_con_la_ruta_del_campo() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(RUTA, params={"periodo": "15d"})

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert [detalle["path"] for detalle in respuesta.json()["details"]] == ["periodo"]


async def test_sin_la_vista_de_inicio_responde_403_y_sin_sesion_401() -> None:
    async with _cliente(sesion=una_sesion(roles=())) as cliente:
        sin_vista = await cliente.get(RUTA)
    async with _cliente(con_sesion=False) as cliente:
        anonimo = await cliente.get(RUTA)

    assert (sin_vista.status_code, anonimo.status_code) == (HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED)
