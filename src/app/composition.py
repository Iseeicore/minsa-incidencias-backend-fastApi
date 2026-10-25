from dataclasses import dataclass
from importlib.metadata import version
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.acceso.adapters.http.router import build_acceso_router
from app.catalogos.adapters.http.areas_router import build_areas_router
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
from app.filtro_corrupcion.adapters.http.router import build_filtro_corrupcion_router
from app.health.router import build_health_router
from app.incidencias.adapters.http.router import build_incidencias_router
from app.incidencias.adapters.http.router_de_acciones import build_acciones_router
from app.incidencias.adapters.http.router_de_analisis import build_analisis_router
from app.incidencias.adapters.http.router_de_derivaciones import build_derivaciones_router
from app.incidencias.adapters.http.router_de_indicadores import build_indicadores_router
from app.incidencias.adapters.http.router_de_ipress import build_ipress_router
from app.shared.body_limit import BodyLimitMiddleware
from app.shared.csrf import CsrfMiddleware
from app.shared.http_errors import UnexpectedErrorMiddleware, register_error_handlers
from app.shared.openapi import drop_default_validation_response
from app.shared.rate_limit import RateLimitMiddleware
from app.shared.security_headers import SecurityHeadersMiddleware
from app.shared.session_middleware import SessionMiddleware
from app.usuarios.adapters.http.router import build_usuarios_router

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractAsyncContextManager

    from app.acceso.application.cerrar_sesion import CerrarSesion
    from app.acceso.application.iniciar_sesion import IniciarSesion
    from app.catalogos.application.listar_areas import ListarAreas
    from app.catalogos.application.listar_plazos import ListarPlazos
    from app.filtro_corrupcion.application.evaluar_corrupcion import EvaluarCorrupcion
    from app.incidencias.application.consulta_de_ipress import (
        ConsultarIncidenciaDeIpress,
        ContarIncidenciasDeIpress,
        ContenidoDeEvidenciaDeIpress,
        ListarIncidenciasDeIpress,
        ObtenerIndicadoresDeIpress,
        ObtenerResumenDeIpress,
    )
    from app.incidencias.application.consultar_analisis import ConsultarAnalisis
    from app.incidencias.application.consultar_derivacion import ConsultarDerivacion
    from app.incidencias.application.consultar_incidencia import ConsultarIncidencia
    from app.incidencias.application.contar_derivaciones import ContarDerivaciones
    from app.incidencias.application.contar_incidencias import ContarIncidencias
    from app.incidencias.application.contenido_de_evidencia import ContenidoDeEvidencia
    from app.incidencias.application.contenido_de_evidencia_derivada import ContenidoDeEvidenciaDerivada
    from app.incidencias.application.ejecutar_accion import EjecutarAccion
    from app.incidencias.application.incidencias_por_vencer import IncidenciasPorVencer
    from app.incidencias.application.listar_derivaciones import ListarDerivaciones
    from app.incidencias.application.listar_incidencias import ListarIncidencias
    from app.incidencias.application.listar_ipress import ListarIpress
    from app.incidencias.application.obtener_indicadores import ObtenerIndicadores
    from app.shared.clock import Clock
    from app.shared.http_security import HttpSecurity
    from app.shared.ports import DatabaseProbe, SessionResolver
    from app.shared.token_bucket import TokenBucketLimiter
    from app.usuarios.application.actualizar_usuario import ActualizarUsuario
    from app.usuarios.application.crear_usuario import CrearUsuario
    from app.usuarios.application.listar_usuarios import ListarUsuarios
    from app.usuarios.application.restablecer_clave import RestablecerClave

type Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]

SERVICE_VERSION = version("migracion-fast-api")
CONTRACT_VERSION = "1.0.0"
V1_PREFIX = "/v1"


@dataclass(frozen=True, slots=True)
class Container:
    listar_plazos: ListarPlazos
    listar_areas: ListarAreas
    iniciar_sesion: IniciarSesion
    cerrar_sesion: CerrarSesion
    listar_usuarios: ListarUsuarios
    crear_usuario: CrearUsuario
    actualizar_usuario: ActualizarUsuario
    restablecer_clave: RestablecerClave
    listar_incidencias: ListarIncidencias
    contar_incidencias: ContarIncidencias
    incidencias_por_vencer: IncidenciasPorVencer
    consultar_incidencia: ConsultarIncidencia
    contenido_de_evidencia: ContenidoDeEvidencia
    ejecutar_accion: EjecutarAccion
    listar_derivaciones: ListarDerivaciones
    contar_derivaciones: ContarDerivaciones
    consultar_derivacion: ConsultarDerivacion
    contenido_de_evidencia_derivada: ContenidoDeEvidenciaDerivada
    consultar_analisis: ConsultarAnalisis
    evaluar_corrupcion: EvaluarCorrupcion
    obtener_indicadores: ObtenerIndicadores
    listar_ipress: ListarIpress
    resumen_de_ipress: ObtenerResumenDeIpress
    indicadores_de_ipress: ObtenerIndicadoresDeIpress
    listar_incidencias_de_ipress: ListarIncidenciasDeIpress
    contar_incidencias_de_ipress: ContarIncidenciasDeIpress
    consultar_incidencia_de_ipress: ConsultarIncidenciaDeIpress
    contenido_de_evidencia_de_ipress: ContenidoDeEvidenciaDeIpress
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
    drop_default_validation_response(app)
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
    app.include_router(
        build_acceso_router(
            container.iniciar_sesion,
            container.cerrar_sesion,
            container.limiter,
            container.security,
            container.clock,
        )
    )
    app.include_router(build_areas_router(container.listar_areas))
    app.include_router(build_catalogos_router(container.listar_plazos))
    app.include_router(
        build_incidencias_router(
            container.listar_incidencias,
            container.contar_incidencias,
            container.incidencias_por_vencer,
            container.consultar_incidencia,
            container.contenido_de_evidencia,
        )
    )
    app.include_router(build_acciones_router(container.ejecutar_accion))
    app.include_router(
        build_derivaciones_router(
            container.listar_derivaciones,
            container.contar_derivaciones,
            container.consultar_derivacion,
            container.contenido_de_evidencia_derivada,
        )
    )
    app.include_router(build_analisis_router(container.consultar_analisis))
    app.include_router(build_filtro_corrupcion_router(container.evaluar_corrupcion))
    app.include_router(build_indicadores_router(container.obtener_indicadores))
    app.include_router(
        build_ipress_router(
            container.listar_ipress,
            container.resumen_de_ipress,
            container.indicadores_de_ipress,
            container.listar_incidencias_de_ipress,
            container.contar_incidencias_de_ipress,
            container.consultar_incidencia_de_ipress,
            container.contenido_de_evidencia_de_ipress,
        )
    )
    app.include_router(
        build_usuarios_router(
            container.listar_usuarios,
            container.crear_usuario,
            container.actualizar_usuario,
            container.restablecer_clave,
        )
    )
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
