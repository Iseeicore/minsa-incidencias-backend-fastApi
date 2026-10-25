import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.catalogos.adapters.persistence.repository import SqlPlazoRepository
from app.enums.categoria_incidencia import CategoriaIncidencia
from tests.helpers.builders import los_plazos_del_catalogo

pytestmark = pytest.mark.integration


async def test_devuelve_los_plazos_de_las_categorias_activas_en_el_orden_del_catalogo(engine: AsyncEngine) -> None:
    assert await SqlPlazoRepository(engine).plazos_por_categoria() == los_plazos_del_catalogo()


async def test_deja_fuera_una_categoria_desactivada(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(text("SELECT set_config('app.actor', 'sistema:prueba', true)"))
        await connection.execute(text("UPDATE catalogo.categoria_incidencia SET activo = false WHERE codigo = 'OTRO'"))

    categorias = [plazo.categoria for plazo in await SqlPlazoRepository(engine).plazos_por_categoria()]

    assert CategoriaIncidencia.OTRO not in categorias
    assert len(categorias) == len(CategoriaIncidencia) - 1
