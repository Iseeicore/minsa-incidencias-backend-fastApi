import asyncio
from typing import TYPE_CHECKING

from app.constants.incidencias import POR_VENCER_LISTA_MAXIMA
from app.incidencias.application.armar_caso import resumir
from app.incidencias.application.visibilidad import visibilidad_de
from app.incidencias.domain.casos import CasosPorVencer
from app.shared.acciones_permitidas import reglas_de_avisos

if TYPE_CHECKING:
    from app.incidencias.application.ports import IncidenciaReader
    from app.incidencias.domain.plazo import PlazosConfigurados
    from app.shared.sesion import SesionActual


class IncidenciasPorVencer:
    def __init__(self, casos: IncidenciaReader, plazos: PlazosConfigurados) -> None:
        self._casos = casos
        self._plazos = plazos

    async def execute(self, sesion: SesionActual) -> CasosPorVencer:
        visible = visibilidad_de(sesion)
        pendientes = reglas_de_avisos(sesion.roles)
        aviso = self._plazos.aviso_horas
        conteo, filas = await asyncio.gather(
            self._casos.contar_por_vencer(visible, aviso, pendientes),
            self._casos.listar_por_vencer(visible, aviso, POR_VENCER_LISTA_MAXIMA, pendientes),
        )
        return CasosPorVencer(
            total=conteo.total,
            por_vencer=conteo.total - conteo.vencidos,
            vencidos=conteo.vencidos,
            casos=tuple(resumir(fila, sesion, self._plazos) for fila in filas),
        )
