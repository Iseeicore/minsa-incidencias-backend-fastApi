import asyncio
import os
import selectors
import uuid
from collections.abc import AsyncIterator, Callable

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.nota.adapters.persistence.tables import metadata

TEST_DATABASE_URL = "TEST_DATABASE_URL"


def pytest_asyncio_loop_factories(
    config: pytest.Config,  # noqa: ARG001
    item: pytest.Item,  # noqa: ARG001
) -> dict[str, Callable[[], asyncio.AbstractEventLoop]]:
    return {"selector": lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())}


def _admin_url() -> str:
    url = os.environ.get(TEST_DATABASE_URL)
    if not url:
        pytest.fail(f"{TEST_DATABASE_URL} no está definida: las pruebas de integración necesitan una base PostgreSQL")
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    admin_url = make_url(_admin_url())
    name = f"test_{uuid.uuid4().hex}"
    admin = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as connection:
        await connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_async_engine(admin_url.set(database=name))
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    yield engine
    await engine.dispose()
    async with admin.connect() as connection:
        await connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    await admin.dispose()
