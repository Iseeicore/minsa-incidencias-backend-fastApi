import asyncio
import selectors
import sys

import uvicorn

from app.config.settings import get_settings


def run() -> None:
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


if __name__ == "__main__":
    run()
