from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request

from app.constants.http import SESSION_STATE_KEY
from app.constants.sesion import SESSION_INVALID_STATE_KEY
from app.errors.sesion_invalida import SesionInvalida
from app.errors.sin_permiso import SinPermiso
from app.errors.sin_sesion import SinSesion
from app.shared.sesion import SesionActual

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.enums.rol_codigo import RolCodigo
    from app.enums.vista_codigo import VistaCodigo


def require_session(request: Request) -> SesionActual:
    sesion = getattr(request.state, SESSION_STATE_KEY, None)
    if isinstance(sesion, SesionActual):
        return sesion
    if getattr(request.state, SESSION_INVALID_STATE_KEY, False):
        raise SesionInvalida
    raise SinSesion


def require_vista(vista: VistaCodigo) -> Callable[[SesionActual], SesionActual]:
    def dependency(sesion: Annotated[SesionActual, Depends(require_session)]) -> SesionActual:
        if vista not in sesion.vistas:
            raise SinPermiso
        return sesion

    return dependency


def require_vista_y_rol(vista: VistaCodigo, *roles: RolCodigo) -> Callable[[SesionActual], SesionActual]:
    def dependency(sesion: Annotated[SesionActual, Depends(require_session)]) -> SesionActual:
        if vista not in sesion.vistas or not any(rol in sesion.roles for rol in roles):
            raise SinPermiso
        return sesion

    return dependency


def require_rol(*roles: RolCodigo) -> Callable[[SesionActual], SesionActual]:
    def dependency(sesion: Annotated[SesionActual, Depends(require_session)]) -> SesionActual:
        if not any(rol in sesion.roles for rol in roles):
            raise SinPermiso
        return sesion

    return dependency
