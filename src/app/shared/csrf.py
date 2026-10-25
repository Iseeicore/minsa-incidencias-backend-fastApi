from typing import TYPE_CHECKING

from starlette.datastructures import Headers
from starlette.requests import Request

from app.constants.http import ORIGIN_HEADER, SAFE_METHODS
from app.errors.origen_no_permitido import OrigenNoPermitido
from app.shared.http_errors import domain_error_response

if TYPE_CHECKING:
    from collections.abc import Collection

    from starlette.types import ASGIApp, Receive, Scope, Send

    from app.shared.clock import Clock


class CsrfMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: Collection[str], clock: Clock) -> None:
        self._app = app
        self._allowed_origins = frozenset(allowed_origins)
        self._clock = clock

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in SAFE_METHODS:
            await self._app(scope, receive, send)
            return
        origin = Headers(scope=scope).get(ORIGIN_HEADER)
        if not origin or origin in self._allowed_origins:
            await self._app(scope, receive, send)
            return
        response = domain_error_response(Request(scope), self._clock, OrigenNoPermitido())
        await response(scope, receive, send)
