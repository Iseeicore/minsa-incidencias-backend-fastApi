import pytest

from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.contract import openapi_raiz, validar_contrato


@pytest.mark.parametrize("ruta", ["/salud", "/salud/listo"])
@pytest.mark.parametrize("base_disponible", [True, False], ids=["con-base", "sin-base"])
async def test_la_salud_cumple_el_contrato(ruta: str, base_disponible: bool) -> None:  # noqa: FBT001
    contenedor = un_contenedor(base_disponible=base_disponible)
    async with un_cliente(contenedor) as cliente:
        validar_contrato(openapi_raiz(contenedor), await cliente.get(ruta))
