import pytest

from app.errors.database_timeout import DatabaseTimeout
from app.errors.database_unavailable import DatabaseUnavailable
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import una_nota
from tests.helpers.contract import openapi_v1, validar_contrato
from tests.helpers.fakes import InMemoryNotaRepository, RaisingNotaRepository

CUERPO_VALIDO = {"titulo": "Titulo", "contenido": "Contenido"}


async def test_crear_cumple_el_contrato_en_exito() -> None:
    contenedor = un_contenedor()
    async with un_cliente(contenedor) as cliente:
        validar_contrato(openapi_v1(contenedor), await cliente.post("/v1/notas", json=CUERPO_VALIDO))


@pytest.mark.parametrize(
    "cuerpo",
    [{"titulo": " ", "contenido": "x"}, {"titulo": "solo titulo"}],
    ids=["regla-de-negocio", "cuerpo-invalido"],
)
async def test_crear_cumple_el_contrato_en_error(cuerpo: dict[str, str]) -> None:
    contenedor = un_contenedor()
    async with un_cliente(contenedor) as cliente:
        validar_contrato(openapi_v1(contenedor), await cliente.post("/v1/notas", json=cuerpo))


async def test_consultar_cumple_el_contrato_en_exito() -> None:
    contenedor = un_contenedor(InMemoryNotaRepository([una_nota(2)]))
    async with un_cliente(contenedor) as cliente:
        validar_contrato(openapi_v1(contenedor), await cliente.get("/v1/notas/NOTA-000002"))


@pytest.mark.parametrize("codigo", ["NOTA-000099", "otro"], ids=["no-existe", "formato-invalido"])
async def test_consultar_cumple_el_contrato_en_error(codigo: str) -> None:
    contenedor = un_contenedor()
    async with un_cliente(contenedor) as cliente:
        validar_contrato(openapi_v1(contenedor), await cliente.get(f"/v1/notas/{codigo}"))


@pytest.mark.parametrize("error", [DatabaseUnavailable(), DatabaseTimeout()], ids=["503", "504"])
async def test_los_fallos_de_la_base_cumplen_el_contrato(error: Exception) -> None:
    contenedor = un_contenedor(RaisingNotaRepository(error))
    async with un_cliente(contenedor) as cliente:
        validar_contrato(openapi_v1(contenedor), await cliente.get("/v1/notas/NOTA-000001"))
        validar_contrato(openapi_v1(contenedor), await cliente.post("/v1/notas", json=CUERPO_VALIDO))


async def test_un_cuerpo_demasiado_grande_cumple_el_contrato() -> None:
    contenedor = un_contenedor()
    cuerpo = {"titulo": "t", "contenido": "x" * 200_000}
    async with un_cliente(contenedor) as cliente:
        validar_contrato(openapi_v1(contenedor), await cliente.post("/v1/notas", json=cuerpo))
