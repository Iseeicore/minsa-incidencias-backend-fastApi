from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.constants.actores import ACTOR_USUARIO_INTERNO_PREFIX
from app.constants.database import SET_ACTOR_QUERY
from app.shared.database import translate_database_errors

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine


def actor_usuario_interno(correo: str) -> str:
    return f"{ACTOR_USUARIO_INTERNO_PREFIX}{correo}"


@asynccontextmanager
async def transaction(engine: AsyncEngine, actor: str) -> AsyncIterator[AsyncConnection]:
    with translate_database_errors():
        async with engine.begin() as connection:
            await connection.execute(text(SET_ACTOR_QUERY), {"actor": actor})
            yield connection
