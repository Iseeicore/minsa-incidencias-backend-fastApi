from typing import TYPE_CHECKING

from app.constants.textos.analisis import MENSAJE_SIN_ANALISIS_DE_IA
from app.constants.textos.incidencias import MENSAJE_CASO_NO_ENCONTRADO
from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.armar_analisis import armar_analisis
from app.incidencias.application.visibilidad import visibilidad_de

if TYPE_CHECKING:
    from app.incidencias.application.ports import AnalisisReader, IncidenciaReader
    from app.incidencias.domain.analisis import AnalisisDeIncidencia
    from app.shared.sesion import SesionActual


class ConsultarAnalisis:
    def __init__(self, casos: IncidenciaReader, analisis: AnalisisReader) -> None:
        self._casos = casos
        self._analisis = analisis

    async def execute(self, sesion: SesionActual, codigo: str) -> AnalisisDeIncidencia:
        caso = await self._casos.buscar_por_codigo(codigo, visibilidad_de(sesion))
        if caso is None:
            raise NoEncontrado(MENSAJE_CASO_NO_ENCONTRADO)
        fila = await self._analisis.buscar(caso.id)
        if fila is None:
            raise NoEncontrado(MENSAJE_SIN_ANALISIS_DE_IA)
        return armar_analisis(caso.codigo, fila)
