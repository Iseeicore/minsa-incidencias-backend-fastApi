import pytest

from app.config.settings import Settings
from app.eventos.application.escuchar_cambios import EscucharCambios
from app.eventos.domain.centro_de_eventos import CentroDeEventos
from app.shared.database import create_engine
from app.shared.token_bucket import TokenBucketLimiter
from app.wiring import build_container, build_eventos
from tests.helpers.eventos_en_memoria import TiempoManual
from tests.helpers.registro_en_memoria import RegistroEnMemoria

SECRETO = "s" * 32


def _settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:c@localhost:1/b")
    monkeypatch.setenv("COOKIE_SECRET", SECRETO)
    return Settings(_env_file=None)


async def test_los_eventos_arman_el_centro_y_el_escuchador_de_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch)
    engine = create_engine(settings)

    eventos = build_eventos(settings, engine, RegistroEnMemoria())

    assert isinstance(eventos.centro, CentroDeEventos)
    assert isinstance(eventos.escuchar, EscucharCambios)
    await engine.dispose()


async def test_el_contenedor_comparte_el_centro_de_eventos_con_el_seguimiento_de_sesiones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(monkeypatch)
    engine = create_engine(settings)
    centro = CentroDeEventos(TiempoManual(), RegistroEnMemoria())

    contenedor = build_container(settings, engine, TokenBucketLimiter(), centro)

    assert contenedor.suscribirse_a_eventos is not None
    await engine.dispose()


async def test_sin_un_centro_recibido_el_contenedor_crea_el_suyo(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch)
    engine = create_engine(settings)

    contenedor = build_container(settings, engine, TokenBucketLimiter())

    assert contenedor.suscribirse_a_eventos is not None
    await engine.dispose()
