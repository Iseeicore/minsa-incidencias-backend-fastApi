from typing import TYPE_CHECKING

from app.acceso.adapters.persistence.sesiones import SqlSesionStore
from app.acceso.adapters.persistence.usuarios import SqlUsuarioFinder
from app.acceso.application.cerrar_sesion import CerrarSesion
from app.acceso.application.iniciar_sesion import IniciarSesion
from app.acceso.application.resolver_sesion import ResolverSesion
from app.catalogos.adapters.persistence.areas import SqlAreaFinder
from app.catalogos.adapters.persistence.repository import SqlPlazoRepository
from app.catalogos.application.listar_areas import ListarAreas
from app.catalogos.application.listar_plazos import ListarPlazos
from app.composition import Container
from app.constants.limits import MS_PER_SECOND
from app.constants.sesion import SECONDS_PER_HOUR
from app.enums.node_env import NodeEnv
from app.shared.clock import SystemClock
from app.shared.database import SqlDatabaseProbe
from app.shared.http_security import HttpSecurity
from app.shared.password_hasher import Argon2PasswordHasher
from app.shared.rate_limit import RateLimitPolicies
from app.shared.session_cookie import SessionCookieConfig
from app.shared.token_bucket import BucketPolicy
from app.usuarios.adapters.persistence.repository import SqlUsuarioReader, SqlUsuarioUnitOfWork
from app.usuarios.application.actualizar_usuario import ActualizarUsuario
from app.usuarios.application.crear_usuario import CrearUsuario
from app.usuarios.application.listar_usuarios import ListarUsuarios
from app.usuarios.application.restablecer_clave import RestablecerClave

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from app.config.settings import Settings
    from app.shared.token_bucket import TokenBucketLimiter


def build_security(settings: Settings) -> HttpSecurity:
    window = settings.rate_limit_login_window_seconds
    return HttpSecurity(
        cookies=SessionCookieConfig(
            secrets=(
                settings.cookie_secret.get_secret_value(),
                *(secret.get_secret_value() for secret in settings.cookie_secret_previous),
            ),
            production=settings.node_env == NodeEnv.PRODUCTION,
        ),
        rate_limits=RateLimitPolicies(
            authenticated=BucketPolicy(settings.rate_limit_auth_capacity, settings.rate_limit_window_seconds),
            anonymous=BucketPolicy(settings.rate_limit_anon_capacity, settings.rate_limit_window_seconds),
        ),
        login_by_email=BucketPolicy(settings.rate_limit_login_capacity, window),
        login_by_ip=BucketPolicy(settings.rate_limit_login_ip_capacity, window),
        session_max_age_seconds=settings.session_absolute_hours * SECONDS_PER_HOUR,
        allowed_origins=tuple(settings.cors_origins),
        trust_proxy=settings.trust_proxy,
    )


def build_container(settings: Settings, engine: AsyncEngine, limiter: TokenBucketLimiter) -> Container:
    hasher = Argon2PasswordHasher()
    sesiones = SqlSesionStore(engine)
    usuarios_uow = SqlUsuarioUnitOfWork(engine)
    return Container(
        listar_plazos=ListarPlazos(SqlPlazoRepository(engine)),
        listar_areas=ListarAreas(SqlAreaFinder(engine)),
        iniciar_sesion=IniciarSesion(SqlUsuarioFinder(engine), sesiones, hasher, settings.session_absolute_hours),
        cerrar_sesion=CerrarSesion(sesiones),
        listar_usuarios=ListarUsuarios(SqlUsuarioReader(engine)),
        crear_usuario=CrearUsuario(usuarios_uow, hasher),
        actualizar_usuario=ActualizarUsuario(usuarios_uow),
        restablecer_clave=RestablecerClave(usuarios_uow, hasher),
        database_probe=SqlDatabaseProbe(engine, timeout_seconds=settings.db_connection_timeout_ms / MS_PER_SECOND),
        clock=SystemClock(),
        session_resolver=ResolverSesion(sesiones, settings.session_idle_minutes),
        limiter=limiter,
        security=build_security(settings),
    )
