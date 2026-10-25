from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from app.composition import Container, create_app
from app.config.settings import get_settings
from app.constants.limits import MS_PER_SECOND
from app.nota.adapters.persistence.repository import SqlCodeGenerator, SqlNotaRepository
from app.nota.application.consultar_nota import ConsultarNota
from app.nota.application.crear_nota import CrearNota
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
    notas = SqlNotaRepository(engine)
    container = Container(
        crear_nota=CrearNota(notas, SqlCodeGenerator(engine), clock),
        consultar_nota=ConsultarNota(notas),
        database_probe=SqlDatabaseProbe(engine, timeout_seconds=settings.db_connection_timeout_ms / MS_PER_SECOND),
        clock=clock,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    return create_app(container, lifespan, docs_enabled=settings.docs_enabled, cors_origins=settings.cors_origins)


app = create_production_app()
