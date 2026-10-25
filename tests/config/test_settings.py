import pytest
from pydantic import ValidationError

from app.config.settings import Settings, get_settings

URL_BASE = "postgresql://usuario:clave@localhost:5432/base"
SECRETO = "s" * 32
OTRO_SECRETO = "o" * 32


def con_entorno(monkeypatch: pytest.MonkeyPatch, **variables: str) -> Settings:
    monkeypatch.setenv("DATABASE_URL", URL_BASE)
    monkeypatch.setenv("COOKIE_SECRET", SECRETO)
    for nombre, valor in variables.items():
        monkeypatch.setenv(nombre, valor)
    return Settings(_env_file=None)


@pytest.mark.parametrize("faltante", ["DATABASE_URL", "COOKIE_SECRET"])
def test_falla_al_arrancar_si_falta_una_variable_obligatoria(monkeypatch: pytest.MonkeyPatch, faltante: str) -> None:
    monkeypatch.setenv("DATABASE_URL", URL_BASE)
    monkeypatch.setenv("COOKIE_SECRET", SECRETO)
    monkeypatch.delenv(faltante)

    with pytest.raises(ValidationError, match=faltante.lower()):
        Settings(_env_file=None)


def test_rechaza_un_secreto_de_sesion_corto(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="cookie_secret"):
        con_entorno(monkeypatch, COOKIE_SECRET="corto")


@pytest.mark.parametrize(
    ("entrada", "esperada"),
    [
        (URL_BASE, "postgresql+psycopg://usuario:clave@localhost:5432/base"),
        ("postgres://u:c@h/b", "postgresql+psycopg://u:c@h/b"),
        ("postgresql+psycopg://u:c@h/b", "postgresql+psycopg://u:c@h/b"),
    ],
)
def test_normaliza_la_url_al_driver_psycopg(monkeypatch: pytest.MonkeyPatch, entrada: str, esperada: str) -> None:
    assert con_entorno(monkeypatch, DATABASE_URL=entrada).database_url.get_secret_value() == esperada


def test_rechaza_una_url_que_no_es_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="PostgreSQL"):
        con_entorno(monkeypatch, DATABASE_URL="mysql://u:c@h/b")


@pytest.mark.parametrize(
    ("campo", "esperado"),
    [
        ("port", 3033),
        ("log_level", "info"),
        ("trust_proxy", False),
        ("clasificador_modo", "externo"),
        ("db_pool_max", 10),
        ("db_idle_timeout_ms", 30000),
        ("db_connection_timeout_ms", 5000),
        ("db_statement_timeout_ms", 15000),
        ("session_idle_minutes", 30),
        ("session_absolute_hours", 8),
        ("vigencia_resolucion_dias", 3),
        ("plazo_aviso_horas", 24),
        ("archivado_interval_seconds", 60),
        ("archivado_lote", 1000),
        ("rate_limit_window_seconds", 300),
        ("rate_limit_auth_capacity", 300),
        ("rate_limit_anon_capacity", 100),
        ("rate_limit_login_window_seconds", 900),
        ("rate_limit_login_capacity", 5),
        ("rate_limit_login_ip_capacity", 30),
    ],
)
def test_los_valores_por_defecto_son_los_documentados(
    monkeypatch: pytest.MonkeyPatch, campo: str, esperado: object
) -> None:
    assert getattr(con_entorno(monkeypatch), campo) == esperado


def test_por_defecto_no_hay_origenes_ni_secretos_anteriores(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = con_entorno(monkeypatch)

    assert settings.cors_origins == []
    assert settings.cookie_secret_previous == []


@pytest.mark.parametrize(
    ("campo", "variable", "valor", "esperado"),
    [
        ("port", "PORT", "8080", 8080),
        ("log_level", "LOG_LEVEL", "debug", "debug"),
        ("trust_proxy", "TRUST_PROXY", "true", True),
        ("clasificador_modo", "CLASIFICADOR_MODO", "sondeo", "sondeo"),
        ("db_pool_max", "DB_POOL_MAX", "3", 3),
        ("archivado_lote", "ARCHIVADO_LOTE", "50", 50),
    ],
)
def test_lee_los_valores_del_entorno(
    monkeypatch: pytest.MonkeyPatch, campo: str, variable: str, valor: str, esperado: object
) -> None:
    assert getattr(con_entorno(monkeypatch, **{variable: valor}), campo) == esperado


@pytest.mark.parametrize(
    ("variable", "valor"),
    [
        ("PORT", "0"),
        ("PORT", "70000"),
        ("LOG_LEVEL", "verbose"),
        ("TRUST_PROXY", "yes"),
        ("CLASIFICADOR_MODO", "otro"),
        ("NODE_ENV", "staging"),
        ("DB_POOL_MAX", "0"),
        ("DB_STATEMENT_TIMEOUT_MS", "2147483648"),
        ("SESSION_IDLE_MINUTES", "-1"),
        ("RATE_LIMIT_LOGIN_CAPACITY", "0"),
    ],
)
def test_rechaza_valores_fuera_de_contrato(monkeypatch: pytest.MonkeyPatch, variable: str, valor: str) -> None:
    with pytest.raises(ValidationError, match=variable.lower()):
        con_entorno(monkeypatch, **{variable: valor})


def test_lee_los_origenes_permitidos_separados_por_coma(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = con_entorno(monkeypatch, CORS_ORIGINS="https://app.minsa.gob.pe, http://localhost:4012,")

    assert settings.cors_origins == ["https://app.minsa.gob.pe", "http://localhost:4012"]


@pytest.mark.parametrize("origen", ["*", "https://app.pe/ruta", "app.pe", "ftp://app.pe", "https://app.pe/"])
def test_rechaza_un_origen_que_no_es_esquema_dominio_y_puerto(monkeypatch: pytest.MonkeyPatch, origen: str) -> None:
    with pytest.raises(ValidationError, match="cors_origins"):
        con_entorno(monkeypatch, CORS_ORIGINS=origen)


def test_lee_los_secretos_anteriores_separados_por_coma(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = con_entorno(monkeypatch, COOKIE_SECRET_PREVIOUS=f"{OTRO_SECRETO}, {'p' * 32}")

    assert [secreto.get_secret_value() for secreto in settings.cookie_secret_previous] == [OTRO_SECRETO, "p" * 32]


def test_un_secreto_anterior_vacio_se_ignora(monkeypatch: pytest.MonkeyPatch) -> None:
    assert con_entorno(monkeypatch, COOKIE_SECRET_PREVIOUS="").cookie_secret_previous == []


def test_rechaza_un_secreto_anterior_corto(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="cookie_secret_previous"):
        con_entorno(monkeypatch, COOKIE_SECRET_PREVIOUS="corto")


def test_los_secretos_no_aparecen_al_imprimir_la_configuracion(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = con_entorno(monkeypatch, COOKIE_SECRET_PREVIOUS=OTRO_SECRETO)

    assert SECRETO not in repr(settings)
    assert "clave" not in repr(settings)
    assert OTRO_SECRETO not in repr(settings)


@pytest.mark.parametrize(
    ("node_env", "documentacion"),
    [("production", False), ("development", True), ("test", True)],
)
def test_la_documentacion_solo_se_enciende_fuera_de_produccion(
    monkeypatch: pytest.MonkeyPatch,
    node_env: str,
    documentacion: bool,  # noqa: FBT001
) -> None:
    assert con_entorno(monkeypatch, NODE_ENV=node_env).docs_enabled is documentacion


def test_sin_node_env_se_asume_produccion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NODE_ENV", raising=False)

    assert con_entorno(monkeypatch).docs_enabled is False


def test_get_settings_reutiliza_la_misma_instancia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL_BASE)
    monkeypatch.setenv("COOKIE_SECRET", SECRETO)
    get_settings.cache_clear()

    assert get_settings() is get_settings()
    get_settings.cache_clear()
