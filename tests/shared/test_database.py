import json

import pytest
from psycopg.errors import QueryCanceled
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.config.settings import Settings
from app.errors.database_timeout import DatabaseTimeout
from app.errors.database_unavailable import DatabaseUnavailable
from app.shared.database import SqlDatabaseProbe, create_engine, translate_database_errors
from app.shared.logging import configure_logging


def unos_settings(monkeypatch: pytest.MonkeyPatch, **entorno: str) -> Settings:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:c@localhost:1/b")
    monkeypatch.setenv("COOKIE_SECRET", "s" * 32)
    for nombre, valor in entorno.items():
        monkeypatch.setenv(nombre, valor)
    return Settings(_env_file=None)


async def test_el_motor_toma_el_pool_de_la_configuracion(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = unos_settings(monkeypatch, DB_POOL_MAX="4", DB_CONNECTION_TIMEOUT_MS="2000")

    engine = create_engine(settings)

    assert isinstance(engine.pool, AsyncAdaptedQueuePool)
    assert engine.pool.size() == 4
    assert engine.pool.timeout() == 2
    assert engine.dialect.driver == "psycopg"
    await engine.dispose()


async def test_la_sonda_responde_false_si_la_base_no_atiende(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(unos_settings(monkeypatch, DB_CONNECTION_TIMEOUT_MS="1000"))

    assert await SqlDatabaseProbe(engine, timeout_seconds=1).ping() is False
    await engine.dispose()


async def test_la_sonda_registra_la_causa_cuando_la_base_no_atiende(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("info")
    engine = create_engine(unos_settings(monkeypatch, DB_CONNECTION_TIMEOUT_MS="1000"))

    await SqlDatabaseProbe(engine, timeout_seconds=1).ping()

    eventos = [json.loads(linea) for linea in capsys.readouterr().out.splitlines() if linea.startswith("{")]
    assert [evento["event"] for evento in eventos] == ["database_probe_failed"]
    assert eventos[0]["level"] == "warning"
    await engine.dispose()


def _error_operacional(causa: Exception) -> OperationalError:
    return OperationalError("SELECT 1", {}, causa)


def test_una_consulta_cancelada_por_el_servidor_se_traduce_a_tiempo_agotado() -> None:
    with pytest.raises(DatabaseTimeout), translate_database_errors():
        raise _error_operacional(QueryCanceled())


def test_la_espera_agotada_del_pool_se_traduce_a_tiempo_agotado() -> None:
    with pytest.raises(DatabaseTimeout), translate_database_errors():
        raise PoolTimeoutError


def test_un_fallo_de_conexion_se_traduce_a_base_no_disponible() -> None:
    with pytest.raises(DatabaseUnavailable), translate_database_errors():
        raise _error_operacional(ConnectionError("rechazada"))


def _falla_con_un_error_ajeno() -> None:
    message = "otro"
    raise ValueError(message)


def test_un_error_ajeno_a_la_base_pasa_sin_traducirse() -> None:
    with pytest.raises(ValueError, match="otro"), translate_database_errors():
        _falla_con_un_error_ajeno()
