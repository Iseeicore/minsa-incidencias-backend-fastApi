from http import HTTPStatus

import pytest

from app.errors.database_timeout import DatabaseTimeout
from app.errors.database_unavailable import DatabaseUnavailable
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.fakes import InMemoryPlazoRepository, RaisingPlazoRepository

RUTA = "/v1/catalogos/plazos"
PLAZOS_DEL_CATALOGO = {
    "items": [
        {"categoria": "denuncia-corrupcion", "plazoDiasHabiles": 3, "archivaPorVencimiento": False},
        {"categoria": "queja", "plazoDiasHabiles": 30, "archivaPorVencimiento": True},
        {"categoria": "reclamo", "plazoDiasHabiles": 30, "archivaPorVencimiento": True},
        {"categoria": "otro", "plazoDiasHabiles": 30, "archivaPorVencimiento": True},
    ]
}


async def test_con_sesion_devuelve_los_plazos_con_los_nombres_de_la_api() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == PLAZOS_DEL_CATALOGO


async def test_la_respuesta_solo_trae_la_lista_de_items() -> None:
    async with un_cliente(un_contenedor(InMemoryPlazoRepository([]))) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.json() == {"items": []}


async def test_sin_sesion_responde_401_y_no_consulta_el_catalogo() -> None:
    async with un_cliente(
        un_contenedor(RaisingPlazoRepository(RuntimeError("no debe llamarse"))), con_sesion=False
    ) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()["errorCode"] == "UNAUTHORIZED"


@pytest.mark.parametrize(
    ("error", "estado"),
    [(DatabaseUnavailable(), HTTPStatus.SERVICE_UNAVAILABLE), (DatabaseTimeout(), HTTPStatus.GATEWAY_TIMEOUT)],
    ids=["no-disponible", "tiempo-agotado"],
)
async def test_los_fallos_de_la_base_responden_503_o_504(error: Exception, estado: HTTPStatus) -> None:
    async with un_cliente(un_contenedor(RaisingPlazoRepository(error))) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == estado
