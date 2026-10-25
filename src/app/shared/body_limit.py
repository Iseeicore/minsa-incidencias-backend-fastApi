from http import HTTPStatus
from typing import TYPE_CHECKING

from starlette.datastructures import Headers
from starlette.exceptions import HTTPException

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        declared = Headers(scope=scope).get("content-length", "")
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            if declared.isdigit() and int(declared) > self._max_bytes:
                raise HTTPException(status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._max_bytes:
                    raise HTTPException(status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return message

        await self._app(scope, limited_receive, send)
