from fastapi import Request  # noqa: TC002

from app.constants.http import SESSION_STATE_KEY
from app.errors.sin_sesion import SinSesion
from app.shared.sesion import SesionActual


def require_session(request: Request) -> SesionActual:
    sesion = getattr(request.state, SESSION_STATE_KEY, None)
    if not isinstance(sesion, SesionActual):
        raise SinSesion
    return sesion
