import pytest

from app.errors.database_timeout import DatabaseTimeout
from app.errors.database_unavailable import DatabaseUnavailable
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.contract import openapi_v1, validar_contrato
from tests.helpers.fakes import RaisingPlazoRepository

RUTA = "/v1/catalogos/plazos"


async def test_los_plazos_cumplen_el_contrato_en_exito() -> None:
    contenedor = un_contenedor()
    async with un_cliente(contenedor) as cliente:
        validar_contrato(openapi_v1(contenedor), await cliente.get(RUTA))


async def test_los_plazos_sin_sesion_cumplen_el_contrato() -> None:
    contenedor = un_contenedor()
    async with un_cliente(contenedor, con_sesion=False) as cliente:
        validar_contrato(openapi_v1(contenedor), await cliente.get(RUTA))


@pytest.mark.parametrize("error", [DatabaseUnavailable(), DatabaseTimeout()], ids=["no-disponible", "tiempo-agotado"])
async def test_los_fallos_de_la_base_cumplen_el_contrato(error: Exception) -> None:
    contenedor = un_contenedor(RaisingPlazoRepository(error))
    async with un_cliente(contenedor) as cliente:
        validar_contrato(openapi_v1(contenedor), await cliente.get(RUTA))
