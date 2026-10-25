from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.enums.alcance_de_usuarios import AlcanceDeUsuarios
from app.enums.rol_codigo import RolCodigo
from app.enums.vista_codigo import VistaCodigo

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class GestionDeUsuarios:
    alcance: AlcanceDeUsuarios
    roles_asignables: tuple[RolCodigo, ...]


@dataclass(frozen=True, slots=True)
class PermisosDelRol:
    vistas: tuple[VistaCodigo, ...]
    usuarios: GestionDeUsuarios | None
    ve_sin_categoria: bool
    ve_todas_las_areas: bool
    avisa_todo_lo_abierto: bool
    cuenta_todas_las_areas: bool


TODAS_LAS_VISTAS = tuple(VistaCodigo)
ROLES_ASIGNABLES = (RolCodigo.ADMINISTRADOR, RolCodigo.GESTOR, RolCodigo.OTRANS, RolCodigo.ESTABLECIMIENTO)


def _sin(*excluidas: VistaCodigo) -> tuple[VistaCodigo, ...]:
    return tuple(vista for vista in TODAS_LAS_VISTAS if vista not in excluidas)


PERMISOS_POR_ROL: Mapping[str, PermisosDelRol] = {
    RolCodigo.ADMINISTRADOR: PermisosDelRol(
        vistas=TODAS_LAS_VISTAS,
        usuarios=GestionDeUsuarios(AlcanceDeUsuarios.TODAS, ROLES_ASIGNABLES),
        ve_sin_categoria=True,
        ve_todas_las_areas=True,
        avisa_todo_lo_abierto=True,
        cuenta_todas_las_areas=True,
    ),
    RolCodigo.GESTOR: PermisosDelRol(
        vistas=_sin(VistaCodigo.DERIVACIONES, VistaCodigo.QR, VistaCodigo.USUARIOS, VistaCodigo.CONSULTA_IPRESS),
        usuarios=None,
        ve_sin_categoria=False,
        ve_todas_las_areas=True,
        avisa_todo_lo_abierto=False,
        cuenta_todas_las_areas=False,
    ),
    RolCodigo.OTRANS: PermisosDelRol(
        vistas=_sin(VistaCodigo.QR, VistaCodigo.USUARIOS),
        usuarios=None,
        ve_sin_categoria=False,
        ve_todas_las_areas=False,
        avisa_todo_lo_abierto=False,
        cuenta_todas_las_areas=False,
    ),
    RolCodigo.ESTABLECIMIENTO: PermisosDelRol(
        vistas=_sin(VistaCodigo.DERIVACIONES, VistaCodigo.CONSULTA_IPRESS),
        usuarios=GestionDeUsuarios(AlcanceDeUsuarios.SU_AREA, (RolCodigo.GESTOR, RolCodigo.ESTABLECIMIENTO)),
        ve_sin_categoria=False,
        ve_todas_las_areas=False,
        avisa_todo_lo_abierto=False,
        cuenta_todas_las_areas=False,
    ),
}


def _permisos_de(roles: Iterable[str]) -> list[PermisosDelRol]:
    return [PERMISOS_POR_ROL[rol] for rol in roles if rol in PERMISOS_POR_ROL]


def vistas_de_roles(roles: Iterable[str]) -> tuple[VistaCodigo, ...]:
    habilitadas = {vista for permisos in _permisos_de(roles) for vista in permisos.vistas}
    return tuple(vista for vista in TODAS_LAS_VISTAS if vista in habilitadas)


def ve_todas_las_areas(roles: Iterable[str]) -> bool:
    return any(permisos.ve_todas_las_areas for permisos in _permisos_de(roles))


def gestion_de_usuarios(roles: Iterable[str]) -> GestionDeUsuarios | None:
    alcance: AlcanceDeUsuarios | None = None
    asignables: dict[RolCodigo, None] = {}
    for permisos in _permisos_de(roles):
        gestion = permisos.usuarios
        if gestion is None:
            continue
        if alcance is None or gestion.alcance == AlcanceDeUsuarios.TODAS:
            alcance = gestion.alcance
        asignables.update(dict.fromkeys(gestion.roles_asignables))
    return None if alcance is None else GestionDeUsuarios(alcance, tuple(asignables))
