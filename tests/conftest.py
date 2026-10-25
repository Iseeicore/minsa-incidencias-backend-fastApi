import asyncio
import os
import re
import selectors
import uuid
from collections.abc import AsyncIterator, Callable

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

TEST_DATABASE_URL = "TEST_DATABASE_URL"
TEST_TEMPLATE_DATABASE = "TEST_TEMPLATE_DATABASE"
PLANTILLA_POR_DEFECTO = "bd_plantilla_desechable"
SUFIJOS_DESECHABLES = ("_desechable", "_dev", "_local")
NOMBRE_VALIDO = re.compile(r"^[a-z0-9_]+$")


def pytest_asyncio_loop_factories(
    config: pytest.Config,  # noqa: ARG001
    item: pytest.Item,  # noqa: ARG001
) -> dict[str, Callable[[], asyncio.AbstractEventLoop]]:
    return {"selector": lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())}


def _plantilla() -> str:
    return os.environ.get(TEST_TEMPLATE_DATABASE, PLANTILLA_POR_DEFECTO)


def pytest_collection_finish(session: pytest.Session) -> None:
    if not any(item.get_closest_marker("integration") for item in session.items):
        return
    if not os.environ.get(TEST_DATABASE_URL):
        pytest.exit(
            f"{TEST_DATABASE_URL} no está definida: las pruebas de integración necesitan una base PostgreSQL",
            returncode=2,
        )
    plantilla = _plantilla()
    if not NOMBRE_VALIDO.fullmatch(plantilla) or not plantilla.endswith(SUFIJOS_DESECHABLES):
        pytest.exit(
            f"{TEST_TEMPLATE_DATABASE} debe ser una base desechable (termina en {', '.join(SUFIJOS_DESECHABLES)})",
            returncode=2,
        )


def _admin_url() -> str:
    return os.environ[TEST_DATABASE_URL].replace("postgresql://", "postgresql+psycopg://", 1)


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    admin_url = make_url(_admin_url())
    name = f"test_{uuid.uuid4().hex}"
    admin = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as connection:
        await connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE "{_plantilla()}"'))
    engine = create_async_engine(admin_url.set(database=name))
    yield engine
    await engine.dispose()
    async with admin.connect() as connection:
        await connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    await admin.dispose()
