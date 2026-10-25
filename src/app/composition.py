from dataclasses import dataclass
from importlib.metadata import version
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.catalogos.adapters.http.router import build_catalogos_router
from app.constants.http import (
    CORS_ALLOWED_HEADERS,
    CORS_ALLOWED_METHODS,
    CORS_EXPOSED_HEADERS,
    DOCS_PATH,
    OPENAPI_PATH,
    REDOC_PATH,
)
from app.constants.limits import CORS_MAX_AGE_SECONDS, JSON_BODY_LIMIT_BYTES
from app.health.router import build_health_router
from app.shared.body_limit import BodyLimitMiddleware
from app.shared.csrf import CsrfMiddleware
from app.shared.http_errors import UnexpectedErrorMiddleware, register_error_handlers
from app.shared.rate_limit import RateLimitMiddleware
from app.shared.security_headers import SecurityHeadersMiddleware
from app.shared.session_middleware import SessionMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractAsyncContextManager

    from app.catalogos.application.listar_plazos import ListarPlazos
    from app.shared.clock import Clock
    from app.shared.http_security import HttpSecurity
    from app.shared.ports import DatabaseProbe, SessionResolver
    from app.shared.token_bucket import TokenBucketLimiter

type Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]

SERVICE_VERSION = version("migracion-fast-api")
CONTRACT_VERSION = "1.0.0"
V1_PREFIX = "/v1"


@dataclass(frozen=True, slots=True)
class Container:
    listar_plazos: ListarPlazos
    database_probe: DatabaseProbe
    clock: Clock
    session_resolver: SessionResolver
    limiter: TokenBucketLimiter
    security: HttpSecurity


@dataclass(frozen=True, slots=True)
class DocumentationUrls:
    docs: str | None
    redoc: str | None
    openapi: str | None

    @classmethod
    def when(cls, *, enabled: bool) -> DocumentationUrls:
        if enabled:
            return cls(DOCS_PATH, REDOC_PATH, OPENAPI_PATH)
        return cls(None, None, None)


def create_v1_app(container: Container, *, docs_enabled: bool = False) -> FastAPI:
    urls = DocumentationUrls.when(enabled=docs_enabled)
    app = FastAPI(
        title="migracion-fast-api v1",
        version=CONTRACT_VERSION,
        servers=[{"url": V1_PREFIX}],
        docs_url=urls.docs,
        redoc_url=urls.redoc,
        openapi_url=urls.openapi,
    )
    register_error_handlers(app, container.clock)
    app.add_middleware(
        RateLimitMiddleware,
        limiter=container.limiter,
        policies=container.security.rate_limits,
        clock=container.clock,
        trust_proxy=container.security.trust_proxy,
    )
    app.add_middleware(SessionMiddleware, resolver=container.session_resolver, cookies=container.security.cookies)
    app.add_middleware(CsrfMiddleware, allowed_origins=container.security.allowed_origins, clock=container.clock)
    app.add_middleware(UnexpectedErrorMiddleware, clock=container.clock)
    app.include_router(build_catalogos_router(container.listar_plazos))
    return app


def create_app(
    container: Container,
    lifespan: Lifespan | None = None,
    *,
    docs_enabled: bool = False,
) -> FastAPI:
    urls = DocumentationUrls.when(enabled=docs_enabled)
    app = FastAPI(
        title="migracion-fast-api",
        version=SERVICE_VERSION,
        lifespan=lifespan,
        docs_url=urls.docs,
        redoc_url=urls.redoc,
        openapi_url=urls.openapi,
    )
    register_error_handlers(app, container.clock)
    app.add_middleware(UnexpectedErrorMiddleware, clock=container.clock)
    app.add_middleware(BodyLimitMiddleware, max_bytes=JSON_BODY_LIMIT_BYTES)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(container.security.allowed_origins),
        allow_credentials=True,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
        expose_headers=CORS_EXPOSED_HEADERS,
        max_age=CORS_MAX_AGE_SECONDS,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(build_health_router(container.database_probe))
    app.mount(V1_PREFIX, create_v1_app(container, docs_enabled=docs_enabled))
    return app
