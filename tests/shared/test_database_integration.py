import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.shared.database import SqlDatabaseProbe

pytestmark = pytest.mark.integration


async def test_la_sonda_responde_true_si_la_base_atiende(engine: AsyncEngine) -> None:
    assert await SqlDatabaseProbe(engine, timeout_seconds=5).ping() is True
