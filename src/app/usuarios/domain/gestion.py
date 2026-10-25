from typing import TYPE_CHECKING

from app.constants.textos.usuarios import MENSAJE_ROL_NO_ASIGNABLE, MENSAJE_USUARIO_NO_ENCONTRADO
from app.enums.alcance_de_usuarios import AlcanceDeUsuarios
from app.errors.no_encontrado import NoEncontrado
from app.errors.sin_permiso import SinPermiso
from app.shared.permisos import gestion_de_usuarios
from app.usuarios.domain.pedidos import RestriccionDeArea

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.enums.rol_codigo import RolCodigo
    from app.shared.permisos import GestionDeUsuarios
    from app.shared.sesion import SesionActual


def exigir_gestion(roles: Iterable[str]) -> GestionDeUsuarios:
    gestion = gestion_de_usuarios(roles)
    if gestion is None:
        raise SinPermiso
    return gestion


def exigir_rol_asignable(gestion: GestionDeUsuarios, rol: RolCodigo) -> None:
    if rol not in gestion.roles_asignables:
        raise SinPermiso(MENSAJE_ROL_NO_ASIGNABLE)


def restriccion_de(sesion: SesionActual, gestion: GestionDeUsuarios) -> RestriccionDeArea | None:
    if gestion.alcance != AlcanceDeUsuarios.SU_AREA:
        return None
    return RestriccionDeArea(sesion.area.id if sesion.area is not None else None)


def usuario_no_encontrado() -> NoEncontrado:
    return NoEncontrado(MENSAJE_USUARIO_NO_ENCONTRADO)
