from typing import TYPE_CHECKING

from app.incidencias.domain.consultas import VisibilidadDeDerivaciones, VisibilidadOperativa
from app.shared.permisos import ve_casos_sin_categoria

if TYPE_CHECKING:
    from app.incidencias.domain.consultas import Visibilidad
    from app.shared.sesion import SesionActual


VISIBILIDAD_DE_DERIVACIONES = VisibilidadDeDerivaciones()


def visibilidad_de(sesion: SesionActual) -> VisibilidadOperativa:
    return VisibilidadOperativa(
        roles=sesion.roles,
        ver_sin_categoria=ve_casos_sin_categoria(sesion.roles),
        area_id=sesion.area.id if sesion.area is not None else None,
    )


def visibilidad_o_de(sesion: SesionActual, visible: Visibilidad | None) -> Visibilidad:
    return visible if visible is not None else visibilidad_de(sesion)
