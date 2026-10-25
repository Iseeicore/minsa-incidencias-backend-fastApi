import asyncio
import selectors
import sys

import uvicorn

from app.clasificador_externo import ejecutar_clasificador
from app.config.settings import get_settings

COMANDO_CLASIFICADOR = "clasificador"
OPCION_UNA_VEZ = "--una-vez"


def servir() -> None:
    settings = get_settings()
    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.port,
        proxy_headers=settings.trust_proxy,
    )
    server = uvicorn.Server(config)
    if sys.platform == "win32":
        asyncio.run(server.serve(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    else:
        server.run()


def run() -> None:
    argumentos = sys.argv[1:]
    if argumentos[:1] == [COMANDO_CLASIFICADOR]:
        sys.exit(ejecutar_clasificador(una_vez=OPCION_UNA_VEZ in argumentos))
    servir()


if __name__ == "__main__":
    run()
