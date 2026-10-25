from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.constants.database import SET_ACTOR_QUERY
from app.shared.database import translate_database_errors
from app.shared.reglas_de_la_base import translate_database_rules

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine


@asynccontextmanager
async def transaction(engine: AsyncEngine, actor: str) -> AsyncIterator[AsyncConnection]:
    with translate_database_errors(), translate_database_rules():
        async with engine.begin() as connection:
            await connection.execute(text(SET_ACTOR_QUERY), {"actor": actor})
            yield connection
