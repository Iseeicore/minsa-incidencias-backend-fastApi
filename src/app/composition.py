from dataclasses import dataclass
from importlib.metadata import version
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from app.nota.adapters.http.router import build_nota_router
from app.shared.body_limit import BodyLimitMiddleware
from app.shared.http_errors import UnexpectedErrorMiddleware, register_error_handlers
from app.shared.security_headers import SecurityHeadersMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from contextlib import AbstractAsyncContextManager

    from app.nota.application.consultar_nota import ConsultarNota
    from app.nota.application.crear_nota import CrearNota
    from app.shared.clock import Clock
    from app.shared.ports import DatabaseProbe

type Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]

SERVICE_VERSION = version("migracion-fast-api")
CONTRACT_VERSION = "1.0.0"
V1_PREFIX = "/v1"


@dataclass(frozen=True, slots=True)
class Container:
    crear_nota: CrearNota
    consultar_nota: ConsultarNota
    database_probe: DatabaseProbe
    clock: Clock


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
    app.add_middleware(UnexpectedErrorMiddleware, clock=container.clock)
    app.include_router(build_nota_router(container.crear_nota, container.consultar_nota))
    return app


def create_app(
    container: Container,
    lifespan: Lifespan | None = None,
    *,
    docs_enabled: bool = False,
    cors_origins: Sequence[str] = (),
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
        allow_origins=list(cors_origins),
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
