from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.enums.accion_incidencia import AccionIncidencia
from app.enums.alcance_de_usuarios import AlcanceDeUsuarios
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.rol_codigo import RolCodigo
from app.enums.vista_codigo import VistaCodigo

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class GestionDeUsuarios:
    alcance: AlcanceDeUsuarios
    roles_asignables: tuple[RolCodigo, ...]


@dataclass(frozen=True, slots=True)
class ReglaDeAccion:
    accion: AccionIncidencia
    estados: tuple[EstadoIncidencia, ...]
    categorias: tuple[CategoriaIncidencia, ...] | None = None
    revisada: bool | None = None
    categorias_destino: tuple[CategoriaIncidencia, ...] | None = None


@dataclass(frozen=True, slots=True)
class PermisosDelRol:
    vistas: tuple[VistaCodigo, ...]
    usuarios: GestionDeUsuarios | None
    ve_sin_categoria: bool
    ve_todas_las_areas: bool
    avisa_todo_lo_abierto: bool
    cuenta_todas_las_areas: bool
    acciones: tuple[ReglaDeAccion, ...] = ()


TODAS_LAS_VISTAS = tuple(VistaCodigo)
ROLES_ASIGNABLES = (RolCodigo.ADMINISTRADOR, RolCodigo.GESTOR, RolCodigo.OTRANS, RolCodigo.ESTABLECIMIENTO)

CLASIFICADO = EstadoIncidencia.CLASIFICADO
DERIVADO = EstadoIncidencia.DERIVADO
EN_GESTION = EstadoIncidencia.EN_GESTION
ARCHIVADO = EstadoIncidencia.ARCHIVADO
DENUNCIA = CategoriaIncidencia.DENUNCIA_CORRUPCION
CATEGORIAS_DEL_AREA = (CategoriaIncidencia.QUEJA, CategoriaIncidencia.RECLAMO, CategoriaIncidencia.OTRO)
CATEGORIAS_AL_CORREGIR_EN_EL_AREA = (*CATEGORIAS_DEL_AREA, DENUNCIA)
ESTADOS_ARCHIVABLES = (CLASIFICADO, DERIVADO, EN_GESTION)

ACCIONES_DE_REVISION_EN_EL_AREA = (
    ReglaDeAccion(AccionIncidencia.CONFIRMAR, (CLASIFICADO,), CATEGORIAS_DEL_AREA, revisada=False),
    ReglaDeAccion(
        AccionIncidencia.CORREGIR,
        (CLASIFICADO,),
        CATEGORIAS_DEL_AREA,
        revisada=False,
        categorias_destino=CATEGORIAS_AL_CORREGIR_EN_EL_AREA,
    ),
    ReglaDeAccion(AccionIncidencia.TOMAR, (CLASIFICADO,), CATEGORIAS_DEL_AREA, revisada=True),
    ReglaDeAccion(AccionIncidencia.TOMAR, (DERIVADO,), CATEGORIAS_DEL_AREA),
    ReglaDeAccion(AccionIncidencia.RESOLVER, (EN_GESTION, DERIVADO), CATEGORIAS_DEL_AREA),
    ReglaDeAccion(AccionIncidencia.ARCHIVAR, ESTADOS_ARCHIVABLES, CATEGORIAS_DEL_AREA),
    ReglaDeAccion(AccionIncidencia.REABRIR, (ARCHIVADO,), CATEGORIAS_DEL_AREA),
)


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
        acciones=(
            ReglaDeAccion(AccionIncidencia.CONFIRMAR, (CLASIFICADO,), revisada=False),
            ReglaDeAccion(AccionIncidencia.CORREGIR, (CLASIFICADO,), revisada=False),
            ReglaDeAccion(AccionIncidencia.DERIVAR, (CLASIFICADO,), revisada=True),
            ReglaDeAccion(AccionIncidencia.ARCHIVAR, ESTADOS_ARCHIVABLES),
            ReglaDeAccion(AccionIncidencia.REABRIR, (ARCHIVADO,)),
        ),
    ),
    RolCodigo.GESTOR: PermisosDelRol(
        vistas=_sin(VistaCodigo.DERIVACIONES, VistaCodigo.QR, VistaCodigo.USUARIOS, VistaCodigo.CONSULTA_IPRESS),
        usuarios=None,
        ve_sin_categoria=False,
        ve_todas_las_areas=True,
        avisa_todo_lo_abierto=False,
        cuenta_todas_las_areas=False,
        acciones=(
            *ACCIONES_DE_REVISION_EN_EL_AREA,
            ReglaDeAccion(AccionIncidencia.DERIVAR, (CLASIFICADO,), CATEGORIAS_DEL_AREA, revisada=True),
        ),
    ),
    RolCodigo.OTRANS: PermisosDelRol(
        vistas=_sin(VistaCodigo.QR, VistaCodigo.USUARIOS),
        usuarios=None,
        ve_sin_categoria=False,
        ve_todas_las_areas=False,
        avisa_todo_lo_abierto=False,
        cuenta_todas_las_areas=False,
        acciones=(
            ReglaDeAccion(AccionIncidencia.CONFIRMAR, (CLASIFICADO,), (DENUNCIA,), revisada=False),
            ReglaDeAccion(AccionIncidencia.CORREGIR, (CLASIFICADO,), (DENUNCIA,), revisada=False),
            ReglaDeAccion(AccionIncidencia.DERIVAR, (CLASIFICADO,), (DENUNCIA,), revisada=True),
            ReglaDeAccion(AccionIncidencia.TOMAR, (CLASIFICADO,), (DENUNCIA,), revisada=True),
            ReglaDeAccion(AccionIncidencia.TOMAR, (DERIVADO,), (DENUNCIA,)),
            ReglaDeAccion(AccionIncidencia.RESOLVER, (DERIVADO, EN_GESTION), (DENUNCIA,)),
            ReglaDeAccion(AccionIncidencia.ARCHIVAR, ESTADOS_ARCHIVABLES, (DENUNCIA,)),
            ReglaDeAccion(AccionIncidencia.REABRIR, (ARCHIVADO,), (DENUNCIA,)),
        ),
    ),
    RolCodigo.ESTABLECIMIENTO: PermisosDelRol(
        vistas=_sin(VistaCodigo.DERIVACIONES, VistaCodigo.CONSULTA_IPRESS),
        usuarios=GestionDeUsuarios(AlcanceDeUsuarios.SU_AREA, (RolCodigo.GESTOR, RolCodigo.ESTABLECIMIENTO)),
        ve_sin_categoria=False,
        ve_todas_las_areas=False,
        avisa_todo_lo_abierto=False,
        cuenta_todas_las_areas=False,
        acciones=ACCIONES_DE_REVISION_EN_EL_AREA,
    ),
}


def _permisos_de(roles: Iterable[str]) -> list[PermisosDelRol]:
    return [PERMISOS_POR_ROL[rol] for rol in roles if rol in PERMISOS_POR_ROL]


def vistas_de_roles(roles: Iterable[str]) -> tuple[VistaCodigo, ...]:
    habilitadas = {vista for permisos in _permisos_de(roles) for vista in permisos.vistas}
    return tuple(vista for vista in TODAS_LAS_VISTAS if vista in habilitadas)


def ve_todas_las_areas(roles: Iterable[str]) -> bool:
    return any(permisos.ve_todas_las_areas for permisos in _permisos_de(roles))


def ve_casos_sin_categoria(roles: Iterable[str]) -> bool:
    return any(permisos.ve_sin_categoria for permisos in _permisos_de(roles))


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
