import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.catalogos.adapters.persistence.repository import SqlPlazoRepository
from app.errors.database_unavailable import DatabaseUnavailable

URL_SIN_SERVIDOR = "postgresql+psycopg://u:c@127.0.0.1:1/b"


@pytest.fixture
def engine_sin_servidor() -> AsyncEngine:
    return create_async_engine(URL_SIN_SERVIDOR, pool_timeout=1, connect_args={"connect_timeout": 1})


async def test_consultar_sin_servidor_se_traduce_a_base_no_disponible(engine_sin_servidor: AsyncEngine) -> None:
    with pytest.raises(DatabaseUnavailable):
        await SqlPlazoRepository(engine_sin_servidor).plazos_por_categoria()
