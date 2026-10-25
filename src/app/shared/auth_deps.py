from fastapi import Request  # noqa: TC002

from app.constants.http import SESSION_STATE_KEY
from app.constants.sesion import SESSION_INVALID_STATE_KEY
from app.errors.sesion_invalida import SesionInvalida
from app.errors.sin_sesion import SinSesion
from app.shared.sesion import SesionActual


def require_session(request: Request) -> SesionActual:
    sesion = getattr(request.state, SESSION_STATE_KEY, None)
    if isinstance(sesion, SesionActual):
        return sesion
    if getattr(request.state, SESSION_INVALID_STATE_KEY, False):
        raise SesionInvalida
    raise SinSesion
