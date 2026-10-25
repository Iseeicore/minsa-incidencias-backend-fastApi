from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from app.catalogos.adapters.persistence.repository import SqlPlazoRepository
from app.catalogos.application.listar_plazos import ListarPlazos
from app.composition import Container, create_app
from app.config.settings import get_settings
from app.constants.limits import MS_PER_SECOND
from app.shared.clock import SystemClock
from app.shared.database import SqlDatabaseProbe, create_engine
from app.shared.logging import configure_logging

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI


def create_production_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings)
    clock = SystemClock()
    container = Container(
        listar_plazos=ListarPlazos(SqlPlazoRepository(engine)),
        database_probe=SqlDatabaseProbe(engine, timeout_seconds=settings.db_connection_timeout_ms / MS_PER_SECOND),
        clock=clock,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    return create_app(container, lifespan, docs_enabled=settings.docs_enabled, cors_origins=settings.cors_origins)


app = create_production_app()
