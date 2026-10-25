from typing import TYPE_CHECKING

from app.incidencias.domain.consultas import VisibilidadOperativa
from app.shared.permisos import ve_casos_sin_categoria

if TYPE_CHECKING:
    from app.shared.sesion import SesionActual


def visibilidad_de(sesion: SesionActual) -> VisibilidadOperativa:
    return VisibilidadOperativa(
        roles=sesion.roles,
        ver_sin_categoria=ve_casos_sin_categoria(sesion.roles),
        area_id=sesion.area.id if sesion.area is not None else None,
    )
