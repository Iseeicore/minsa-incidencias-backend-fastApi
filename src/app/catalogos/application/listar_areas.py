from typing import TYPE_CHECKING

from app.catalogos.domain.area_listada import FiltrosDeAreas
from app.shared.cursor import PosicionPorNombre, encode_int_cursor
from app.shared.pagination import limite_con_extra, pagina_de
from app.shared.permisos import ve_todas_las_areas

if TYPE_CHECKING:
    from app.catalogos.application.ports import AreaFinder
    from app.catalogos.domain.area_listada import AreaListada, ConsultaAreas
    from app.shared.pagination import Pagina
    from app.shared.sesion import SesionActual


def _cursor_de(area: AreaListada) -> str:
    return encode_int_cursor(PosicionPorNombre(area.nombre, area.id))


class ListarAreas:
    def __init__(self, areas: AreaFinder) -> None:
        self._areas = areas

    async def execute(self, sesion: SesionActual, consulta: ConsultaAreas) -> Pagina[AreaListada]:
        restringir = not ve_todas_las_areas(sesion.roles)
        filtros = FiltrosDeAreas(
            tipo=consulta.tipo,
            texto=consulta.texto,
            solo_area_id=sesion.area.id if restringir and sesion.area is not None else None,
            restringir_a_un_area=restringir,
        )
        filas = await self._areas.listar(filtros, limite_con_extra(consulta.limite), consulta.despues_de)
        return pagina_de(filas, consulta.limite, _cursor_de)
