from typing import TYPE_CHECKING

from starlette.datastructures import MutableHeaders
from starlette.requests import Request

from app.constants.http import SESSION_STATE_KEY, SET_COOKIE_HEADER
from app.constants.sesion import SESSION_INVALID_STATE_KEY
from app.shared.route_path import is_logout
from app.shared.session_cookie import SessionCookieConfig, clear_cookie_header, read_session_id

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from app.shared.ports import SessionResolver


class SessionMiddleware:
    def __init__(self, app: ASGIApp, resolver: SessionResolver, cookies: SessionCookieConfig) -> None:
        self._app = app
        self._resolver = resolver
        self._cookies = cookies

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or is_logout(scope):
            await self._app(scope, receive, send)
            return
        session_id = read_session_id(Request(scope).cookies, self._cookies)
        if session_id is None:
            await self._app(scope, receive, send)
            return
        sesion = await self._resolver.resolve(session_id)
        state = scope.setdefault("state", {})
        if sesion is not None:
            state[SESSION_STATE_KEY] = sesion
            await self._app(scope, receive, send)
            return
        state[SESSION_INVALID_STATE_KEY] = True

        async def send_clearing_cookie(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append(SET_COOKIE_HEADER, clear_cookie_header(self._cookies))
            await send(message)

        await self._app(scope, receive, send_clearing_cookie)
