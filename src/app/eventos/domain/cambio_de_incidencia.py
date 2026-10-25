from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.enums.rol_codigo import RolCodigo
from app.shared.permisos import cuenta_todas_las_areas, ve_casos_sin_categoria

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

type CategoriasPorRol = Mapping[str, AbstractSet[int]]


@dataclass(frozen=True, slots=True)
class CambioDeIncidencia:
    area_antes: int | None
    area_despues: int | None
    categoria_antes: int | None
    categoria_despues: int | None


@dataclass(frozen=True, slots=True)
class AlcanceDeEventos:
    ve_todo: bool
    ver_sin_categoria: bool
    area_id: int | None
    categorias: frozenset[int]


def alcance_de_eventos(
    roles: Sequence[str], area_id: int | None, categorias_por_rol: CategoriasPorRol
) -> AlcanceDeEventos:
    categorias = frozenset(categoria for rol in roles for categoria in categorias_por_rol.get(rol, ()))
    return AlcanceDeEventos(
        ve_todo=cuenta_todas_las_areas(roles) or RolCodigo.OTRANS in roles,
        ver_sin_categoria=ve_casos_sin_categoria(roles),
        area_id=area_id,
        categorias=categorias,
    )


def recibe_cambio(alcance: AlcanceDeEventos, cambio: CambioDeIncidencia) -> bool:
    if alcance.ve_todo:
        return True
    if alcance.area_id is None:
        return False
    es_de_su_area = alcance.area_id in {cambio.area_antes, cambio.area_despues}

    def la_ve(categoria: int | None) -> bool:
        return alcance.ver_sin_categoria if categoria is None else categoria in alcance.categorias

    return es_de_su_area and (la_ve(cambio.categoria_antes) or la_ve(cambio.categoria_despues))
