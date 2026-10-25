import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.errors.database_unavailable import DatabaseUnavailable
from app.nota.adapters.persistence.repository import SqlCodeGenerator, SqlNotaRepository
from tests.helpers.builders import un_codigo, una_nota

URL_SIN_SERVIDOR = "postgresql+psycopg://u:c@127.0.0.1:1/b"


@pytest.fixture
def engine_sin_servidor() -> AsyncEngine:
    return create_async_engine(URL_SIN_SERVIDOR, pool_timeout=1, connect_args={"connect_timeout": 1})


async def test_guardar_sin_servidor_se_traduce_a_base_no_disponible(engine_sin_servidor: AsyncEngine) -> None:
    with pytest.raises(DatabaseUnavailable):
        await SqlNotaRepository(engine_sin_servidor).save(una_nota())


async def test_consultar_sin_servidor_se_traduce_a_base_no_disponible(engine_sin_servidor: AsyncEngine) -> None:
    with pytest.raises(DatabaseUnavailable):
        await SqlNotaRepository(engine_sin_servidor).find_by_codigo(un_codigo())


async def test_pedir_un_codigo_sin_servidor_se_traduce_a_base_no_disponible(engine_sin_servidor: AsyncEngine) -> None:
    with pytest.raises(DatabaseUnavailable):
        await SqlCodeGenerator(engine_sin_servidor).next_codigo()
