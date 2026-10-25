import asyncio
from typing import TYPE_CHECKING

from app.constants.textos.incidencias import MENSAJE_CASO_NO_ENCONTRADO
from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.armar_caso import detallar
from app.incidencias.application.visibilidad import visibilidad_de

if TYPE_CHECKING:
    from app.incidencias.application.ports import IncidenciaReader
    from app.incidencias.domain.casos import CasoDetalle
    from app.incidencias.domain.plazo import PlazosConfigurados
    from app.shared.sesion import SesionActual


class ConsultarIncidencia:
    def __init__(self, casos: IncidenciaReader, plazos: PlazosConfigurados) -> None:
        self._casos = casos
        self._plazos = plazos

    async def execute(self, sesion: SesionActual, codigo: str) -> CasoDetalle:
        fila = await self._casos.buscar_por_codigo(codigo, visibilidad_de(sesion))
        if fila is None:
            raise NoEncontrado(MENSAJE_CASO_NO_ENCONTRADO)
        evidencias, historial = await asyncio.gather(self._casos.evidencias(fila.id), self._casos.historial(fila.id))
        return detallar(fila, sesion, self._plazos, evidencias, historial)
