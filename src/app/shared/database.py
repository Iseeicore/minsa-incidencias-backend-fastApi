import asyncio
import math
from contextlib import contextmanager
from typing import TYPE_CHECKING, Protocol

import structlog
from psycopg.errors import QueryCanceled
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.constants.database import PROBE_QUERY
from app.constants.limits import MS_PER_SECOND
from app.errors.database_timeout import DatabaseTimeout
from app.errors.database_unavailable import DatabaseUnavailable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pydantic import SecretStr

logger = structlog.get_logger()


class DatabaseConfig(Protocol):
    @property
    def database_url(self) -> SecretStr: ...

    @property
    def db_pool_max(self) -> int: ...

    @property
    def db_idle_timeout_ms(self) -> int: ...

    @property
    def db_connection_timeout_ms(self) -> int: ...

    @property
    def db_statement_timeout_ms(self) -> int: ...


def create_engine(settings: DatabaseConfig) -> AsyncEngine:
    connection_timeout_seconds = settings.db_connection_timeout_ms / MS_PER_SECOND
    session_options = (
        f"-c statement_timeout={settings.db_statement_timeout_ms} "
        f"-c idle_in_transaction_session_timeout={settings.db_statement_timeout_ms}"
    )
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_size=settings.db_pool_max,
        max_overflow=0,
        pool_timeout=connection_timeout_seconds,
        pool_recycle=max(1, settings.db_idle_timeout_ms // MS_PER_SECOND),
        pool_pre_ping=True,
        connect_args={
            "options": session_options,
            "connect_timeout": max(1, math.ceil(connection_timeout_seconds)),
        },
    )


@contextmanager
def translate_database_errors() -> Iterator[None]:
    try:
        yield
    except PoolTimeoutError as error:
        raise DatabaseTimeout from error
    except OperationalError as error:
        if isinstance(error.orig, QueryCanceled):
            raise DatabaseTimeout from error
        raise DatabaseUnavailable from error


class SqlDatabaseProbe:
    def __init__(self, engine: AsyncEngine, timeout_seconds: float) -> None:
        self._engine = engine
        self._timeout_seconds = timeout_seconds

    async def ping(self) -> bool:
        try:
            async with asyncio.timeout(self._timeout_seconds), self._engine.connect() as connection:
                await connection.execute(text(PROBE_QUERY))
        except Exception as error:  # noqa: BLE001
            logger.warning("database_probe_failed", error_type=type(error).__name__, reason=str(error))
            return False
        return True
