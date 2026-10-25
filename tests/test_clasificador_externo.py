import asyncio
import os

import pytest
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from app.clasificador_externo import correr_clasificador
from app.config.settings import Settings
from app.constants.clasificacion import CODIGO_DE_SALIDA_CORRECTO, CODIGO_DE_SALIDA_FALLIDO
from tests.helpers.base import consultar
from tests.helpers.casos import sembrar_caso

COOKIE = "c" * 32
URL_INALCANZABLE = "postgresql+psycopg://u:c@127.0.0.1:1/b"


def _settings(monkeypatch: pytest.MonkeyPatch, url: str) -> Settings:
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("COOKIE_SECRET", COOKIE)
    monkeypatch.setenv("DB_CONNECTION_TIMEOUT_MS", "1000")
    return Settings(_env_file=None)


@pytest.mark.integration
async def test_una_pasada_del_proceso_externo_clasifica_la_cola_y_termina_bien(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    caso = await sembrar_caso(engine, categoria=None, marcador="El personal fue grosero y prepotente conmigo")
    url = make_url(os.environ["TEST_DATABASE_URL"]).set(database=engine.url.database, drivername="postgresql+psycopg")
    settings = _settings(monkeypatch, url.render_as_string(hide_password=False))

    codigo = await asyncio.wait_for(correr_clasificador(settings, asyncio.Event(), una_vez=True), timeout=30)

    [(categoria,)] = await consultar(
        engine,
        "SELECT c.codigo FROM chatbot.incidencia_paciente i"
        " JOIN catalogo.categoria_incidencia c ON c.id = i.categoria_ia_id WHERE i.id = CAST(:id AS uuid)",
        id=caso.id,
    )
    assert (codigo, categoria) == (CODIGO_DE_SALIDA_CORRECTO, "QUEJA")


async def test_si_la_base_no_responde_el_proceso_externo_se_detiene_con_codigo_de_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(monkeypatch, URL_INALCANZABLE)

    codigo = await asyncio.wait_for(correr_clasificador(settings, asyncio.Event(), una_vez=True), timeout=30)

    assert codigo == CODIGO_DE_SALIDA_FALLIDO
