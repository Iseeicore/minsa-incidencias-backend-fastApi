import pytest

from app.config.settings import Settings
from app.shared.database import create_engine
from app.shared.session_cookie import SessionCookieConfig
from app.shared.token_bucket import BucketPolicy, TokenBucketLimiter
from app.wiring import build_container, build_security

SECRETO = "s" * 32
ANTERIOR = "p" * 32


def _settings(monkeypatch: pytest.MonkeyPatch, **entorno: str) -> Settings:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:c@localhost:1/b")
    monkeypatch.setenv("COOKIE_SECRET", SECRETO)
    for nombre, valor in entorno.items():
        monkeypatch.setenv(nombre, valor)
    return Settings(_env_file=None)


def test_la_seguridad_toma_las_cookies_los_limites_y_el_origen_de_la_configuracion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(
        monkeypatch,
        NODE_ENV="production",
        COOKIE_SECRET_PREVIOUS=ANTERIOR,
        CORS_ORIGINS="https://app.minsa.gob.pe",
        TRUST_PROXY="true",
        SESSION_ABSOLUTE_HOURS="8",
        RATE_LIMIT_AUTH_CAPACITY="300",
        RATE_LIMIT_ANON_CAPACITY="100",
        RATE_LIMIT_WINDOW_SECONDS="300",
        RATE_LIMIT_LOGIN_CAPACITY="5",
        RATE_LIMIT_LOGIN_IP_CAPACITY="30",
        RATE_LIMIT_LOGIN_WINDOW_SECONDS="900",
    )

    seguridad = build_security(settings)

    assert seguridad.cookies == SessionCookieConfig(secrets=(SECRETO, ANTERIOR), production=True)
    assert seguridad.rate_limits.authenticated == BucketPolicy(300, 300)
    assert seguridad.rate_limits.anonymous == BucketPolicy(100, 300)
    assert seguridad.login_by_email == BucketPolicy(5, 900)
    assert seguridad.login_by_ip == BucketPolicy(30, 900)
    assert seguridad.session_max_age_seconds == 8 * 3600
    assert seguridad.allowed_origins == ("https://app.minsa.gob.pe",)
    assert seguridad.trust_proxy is True


def test_fuera_de_produccion_la_cookie_no_lleva_el_prefijo_host(monkeypatch: pytest.MonkeyPatch) -> None:
    seguridad = build_security(_settings(monkeypatch, NODE_ENV="development"))

    assert seguridad.cookies.production is False
    assert seguridad.cookies.name == "gestion_sid"


async def test_el_contenedor_arma_todos_los_casos_de_uso_sobre_el_mismo_limitador(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(monkeypatch)
    engine = create_engine(settings)
    limitador = TokenBucketLimiter()

    contenedor = build_container(settings, engine, limitador)

    assert contenedor.limiter is limitador
    assert contenedor.security == build_security(settings)
    for caso in (
        contenedor.listar_plazos,
        contenedor.listar_areas,
        contenedor.iniciar_sesion,
        contenedor.cerrar_sesion,
        contenedor.listar_usuarios,
        contenedor.crear_usuario,
        contenedor.actualizar_usuario,
        contenedor.restablecer_clave,
        contenedor.listar_incidencias,
        contenedor.contar_incidencias,
        contenedor.incidencias_por_vencer,
        contenedor.consultar_incidencia,
        contenedor.contenido_de_evidencia,
        contenedor.session_resolver,
        contenedor.database_probe,
    ):
        assert caso is not None
    await engine.dispose()
