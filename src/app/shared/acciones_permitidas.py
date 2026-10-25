from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.enums.accion_incidencia import AccionIncidencia
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.shared.permisos import PERMISOS_POR_ROL

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.enums.estado_incidencia import EstadoIncidencia
    from app.shared.permisos import ReglaDeAccion

TODAS_LAS_CATEGORIAS = tuple(CategoriaIncidencia)
ACCIONES_EN_ORDEN = tuple(AccionIncidencia)


@dataclass(frozen=True, slots=True)
class CasoParaAcciones:
    estado: EstadoIncidencia
    categoria: CategoriaIncidencia | None
    revisada: bool


def _cumple(regla: ReglaDeAccion, caso: CasoParaAcciones) -> bool:
    if caso.estado not in regla.estados:
        return False
    if regla.categorias is not None and (caso.categoria is None or caso.categoria not in regla.categorias):
        return False
    return regla.revisada is None or regla.revisada == caso.revisada


def _reglas_de(roles: Iterable[str]) -> list[ReglaDeAccion]:
    return [regla for rol in roles if rol in PERMISOS_POR_ROL for regla in PERMISOS_POR_ROL[rol].acciones]


def acciones_permitidas(roles: Iterable[str], caso: CasoParaAcciones) -> list[AccionIncidencia]:
    habilitadas = {regla.accion for regla in _reglas_de(roles) if _cumple(regla, caso)}
    return [accion for accion in ACCIONES_EN_ORDEN if accion in habilitadas]


def categorias_para_corregir(roles: Iterable[str], caso: CasoParaAcciones) -> list[CategoriaIncidencia]:
    permitidas: dict[CategoriaIncidencia, None] = {}
    for regla in _reglas_de(roles):
        if regla.accion == AccionIncidencia.CORREGIR and _cumple(regla, caso):
            permitidas.update(dict.fromkeys(regla.categorias_destino or TODAS_LAS_CATEGORIAS))
    return list(permitidas)


def reglas_de_avisos(roles: Iterable[str]) -> tuple[ReglaDeAccion, ...] | None:
    reglas: list[ReglaDeAccion] = []
    for rol in roles:
        permisos = PERMISOS_POR_ROL.get(rol)
        if permisos is None:
            continue
        if permisos.avisa_todo_lo_abierto:
            return None
        reglas.extend(permisos.acciones)
    return tuple(reglas)
