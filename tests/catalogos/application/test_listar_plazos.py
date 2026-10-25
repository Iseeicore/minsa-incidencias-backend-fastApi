import pytest

from app.catalogos.application.listar_plazos import ListarPlazos
from app.enums.categoria_incidencia import CategoriaIncidencia
from tests.helpers.builders import los_plazos_del_catalogo, un_plazo
from tests.helpers.fakes import InMemoryPlazoRepository, RaisingPlazoRepository


async def test_devuelve_los_plazos_en_el_orden_del_repositorio() -> None:
    plazos = los_plazos_del_catalogo()

    assert await ListarPlazos(InMemoryPlazoRepository(plazos)).execute() == plazos


async def test_sin_categorias_activas_devuelve_una_lista_vacia() -> None:
    assert await ListarPlazos(InMemoryPlazoRepository([])).execute() == []


async def test_no_altera_los_plazos_que_recibe() -> None:
    plazo = un_plazo(CategoriaIncidencia.OTRO, 30, archiva_por_vencimiento=True)

    assert await ListarPlazos(InMemoryPlazoRepository([plazo])).execute() == [plazo]


async def test_deja_pasar_el_error_del_repositorio() -> None:
    with pytest.raises(RuntimeError, match="falla"):
        await ListarPlazos(RaisingPlazoRepository(RuntimeError("falla"))).execute()
