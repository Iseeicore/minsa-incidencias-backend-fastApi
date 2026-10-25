from typing import TYPE_CHECKING

from app.constants.http import SESSION_STATE_KEY

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from app.shared.sesion import SesionActual


class SesionDePrueba:
    def __init__(self, app: ASGIApp, sesion: SesionActual) -> None:
        self._app = app
        self._sesion = sesion

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            scope.setdefault("state", {})[SESSION_STATE_KEY] = self._sesion
        await self._app(scope, receive, send)
