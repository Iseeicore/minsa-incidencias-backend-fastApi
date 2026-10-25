import asyncio
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING

from app.catalogos.adapters.persistence.repository import SqlPlazoRepository
from app.catalogos.application.listar_plazos import ListarPlazos
from app.composition import Container, create_app
from app.config.settings import get_settings
from app.constants.limits import MS_PER_SECOND, RATE_LIMIT_SWEEP_INTERVAL_SECONDS
from app.enums.node_env import NodeEnv
from app.shared.clock import SystemClock
from app.shared.database import SqlDatabaseProbe, create_engine
from app.shared.http_security import HttpSecurity
from app.shared.limiter_sweeper import sweep_forever
from app.shared.logging import configure_logging
from app.shared.rate_limit import RateLimitPolicies
from app.shared.session_cookie import SessionCookieConfig
from app.shared.sin_sesiones import SinSesiones
from app.shared.token_bucket import BucketPolicy, TokenBucketLimiter

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI


def create_production_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings)
    clock = SystemClock()
    limiter = TokenBucketLimiter()
    security = HttpSecurity(
        cookies=SessionCookieConfig(
            secrets=(
                settings.cookie_secret.get_secret_value(),
                *(s.get_secret_value() for s in settings.cookie_secret_previous),
            ),
            production=settings.node_env == NodeEnv.PRODUCTION,
        ),
        rate_limits=RateLimitPolicies(
            authenticated=BucketPolicy(settings.rate_limit_auth_capacity, settings.rate_limit_window_seconds),
            anonymous=BucketPolicy(settings.rate_limit_anon_capacity, settings.rate_limit_window_seconds),
        ),
        allowed_origins=tuple(settings.cors_origins),
        trust_proxy=settings.trust_proxy,
    )
    container = Container(
        listar_plazos=ListarPlazos(SqlPlazoRepository(engine)),
        database_probe=SqlDatabaseProbe(engine, timeout_seconds=settings.db_connection_timeout_ms / MS_PER_SECOND),
        clock=clock,
        session_resolver=SinSesiones(),
        limiter=limiter,
        security=security,
    )

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
