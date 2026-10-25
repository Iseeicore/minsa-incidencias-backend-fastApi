import asyncio
import selectors
import signal
import sys
from typing import TYPE_CHECKING

import structlog

from app.config.settings import get_settings
from app.constants.clasificacion import (
    CODIGO_DE_SALIDA_CORRECTO,
    CODIGO_DE_SALIDA_FALLIDO,
    INTERVALO_SONDEO_SEGUNDOS,
    VERSION_CLASIFICADOR_ALGORITMICO,
)
from app.constants.textos.procesos import (
    EVENTO_CLASIFICADOR_DETENIDO,
    EVENTO_CLASIFICADOR_INICIADO,
    EVENTO_CLASIFICADOR_SE_DETUVO_POR_UN_ERROR,
)
from app.shared.ciclo_periodico import repetir_hasta_parar
from app.shared.database import create_engine
from app.shared.logging import configure_logging
from app.wiring import build_trabajador_clasificador

if TYPE_CHECKING:
    from app.config.settings import Settings


async def correr_clasificador(settings: Settings, parar: asyncio.Event, *, una_vez: bool) -> int:
    registro = structlog.get_logger()
    engine = create_engine(settings)
    trabajador = build_trabajador_clasificador(engine, registro)
    codigo = CODIGO_DE_SALIDA_CORRECTO
    try:
        registro.info(EVENTO_CLASIFICADOR_INICIADO, version_motor=VERSION_CLASIFICADOR_ALGORITMICO, una_vez=una_vez)
        await repetir_hasta_parar(trabajador.ejecutar, parar, INTERVALO_SONDEO_SEGUNDOS, una_vez=una_vez)
    except Exception as error:  # noqa: BLE001
        registro.error(EVENTO_CLASIFICADOR_SE_DETUVO_POR_UN_ERROR, error=type(error).__name__)
        codigo = CODIGO_DE_SALIDA_FALLIDO
    finally:
        await engine.dispose()
        registro.info(EVENTO_CLASIFICADOR_DETENIDO)
    return codigo


async def _correr_hasta_la_senal(settings: Settings, *, una_vez: bool) -> int:
    parar = asyncio.Event()
    bucle = asyncio.get_running_loop()
    for senal in (signal.SIGINT, signal.SIGTERM):
        signal.signal(senal, lambda *_: bucle.call_soon_threadsafe(parar.set))
    return await correr_clasificador(settings, parar, una_vez=una_vez)


def ejecutar_clasificador(*, una_vez: bool) -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    corutina = _correr_hasta_la_senal(settings, una_vez=una_vez)
    fabrica = (lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())) if sys.platform == "win32" else None
    return asyncio.run(corutina, loop_factory=fabrica)
