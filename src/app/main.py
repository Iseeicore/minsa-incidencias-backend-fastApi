import asyncio
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING

from app.composition import create_app
from app.config.settings import get_settings
from app.constants.limits import RATE_LIMIT_SWEEP_INTERVAL_SECONDS
from app.shared.database import create_engine
from app.shared.limiter_sweeper import sweep_forever
from app.shared.logging import configure_logging
from app.shared.token_bucket import TokenBucketLimiter
from app.wiring import build_container

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI


def create_production_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings)
    limiter = TokenBucketLimiter()
    container = build_container(settings, engine, limiter)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        sweeper = asyncio.create_task(sweep_forever(limiter, RATE_LIMIT_SWEEP_INTERVAL_SECONDS))
        yield
        sweeper.cancel()
        with suppress(asyncio.CancelledError):
            await sweeper
        await engine.dispose()

    return create_app(container, lifespan, docs_enabled=settings.docs_enabled)


app = create_production_app()
