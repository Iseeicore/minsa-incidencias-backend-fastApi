from typing import TYPE_CHECKING

from app.constants.textos.incidencias import MENSAJE_CASO_NO_ENCONTRADO, MENSAJE_EVIDENCIA_NO_ENCONTRADA
from app.errors.evidencia_no_disponible import EvidenciaNoDisponible
from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.visibilidad import visibilidad_de
from app.incidencias.domain.imagen_de_evidencia import leer_imagen_de_evidencia

if TYPE_CHECKING:
    from app.incidencias.application.ports import IncidenciaReader
    from app.incidencias.domain.imagen_de_evidencia import ImagenDeEvidencia
    from app.shared.sesion import SesionActual


class ContenidoDeEvidencia:
    def __init__(self, casos: IncidenciaReader) -> None:
        self._casos = casos

    async def execute(self, sesion: SesionActual, codigo: str, evidencia_id: str) -> ImagenDeEvidencia:
        fila = await self._casos.buscar_por_codigo(codigo, visibilidad_de(sesion))
        if fila is None:
            raise NoEncontrado(MENSAJE_CASO_NO_ENCONTRADO)
        ruta = await self._casos.ruta_de_evidencia(fila.id, evidencia_id)
        if ruta is None:
            raise NoEncontrado(MENSAJE_EVIDENCIA_NO_ENCONTRADA)
        imagen = leer_imagen_de_evidencia(ruta)
        if imagen is None:
            raise EvidenciaNoDisponible
        return imagen
