from typing import TYPE_CHECKING

from starlette.datastructures import MutableHeaders

from app.constants.http import SECURITY_HEADERS

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
            await send(message)

        await self._app(scope, receive, send_with_headers)
