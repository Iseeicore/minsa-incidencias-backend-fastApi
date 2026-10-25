import asyncio
import selectors
import sys
from importlib import import_module
from typing import TYPE_CHECKING

import uvicorn

from app.clasificador_externo import ejecutar_clasificador
from app.comandos_de_usuarios import ejecutar_crear_administrador, ejecutar_crear_usuario_de_prueba
from app.config.settings import get_settings
from app.constants.limits import APAGADO_TIMEOUT_SEGUNDOS

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType

COMANDO_CLASIFICADOR = "clasificador"
COMANDO_CREAR_ADMINISTRADOR = "crear-admin"
COMANDO_CREAR_USUARIO_DE_PRUEBA = "crear-usuario-prueba"
OPCION_UNA_VEZ = "--una-vez"


class ServidorConCierreDeEventos(uvicorn.Server):
    def __init__(self, config: uvicorn.Config, cerrar_eventos: Callable[[], None]) -> None:
        super().__init__(config)
        self._cerrar_eventos = cerrar_eventos

    def handle_exit(self, sig: int, frame: FrameType | None) -> None:
        self._cerrar_eventos()
        super().handle_exit(sig, frame)


def servir() -> None:
    app = import_module("app.main").app
    settings = get_settings()
    config = uvicorn.Config(
        app,
        host="0.0.0.0",  # noqa: S104
        port=settings.port,
        proxy_headers=settings.trust_proxy,
        timeout_graceful_shutdown=APAGADO_TIMEOUT_SEGUNDOS,
    )
    server = ServidorConCierreDeEventos(config, app.state.cerrar_eventos)
    if sys.platform == "win32":
        asyncio.run(server.serve(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    else:
        server.run()


def run() -> None:
    argumentos = sys.argv[1:]
    if argumentos[:1] == [COMANDO_CLASIFICADOR]:
        sys.exit(ejecutar_clasificador(una_vez=OPCION_UNA_VEZ in argumentos))
    if argumentos[:1] == [COMANDO_CREAR_ADMINISTRADOR]:
        sys.exit(ejecutar_crear_administrador())
    if argumentos[:1] == [COMANDO_CREAR_USUARIO_DE_PRUEBA]:
        sys.exit(ejecutar_crear_usuario_de_prueba())
    servir()


if __name__ == "__main__":
    run()
