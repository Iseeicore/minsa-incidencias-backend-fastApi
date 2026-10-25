from typing import TYPE_CHECKING

from app.constants.textos.derivaciones import MENSAJE_DERIVACION_NO_DISPONIBLE
from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.armar_derivacion import resumir_derivacion
from app.incidencias.application.visibilidad import VISIBILIDAD_DE_DERIVACIONES
from app.incidencias.domain.derivaciones import DerivacionDetalle

if TYPE_CHECKING:
    from app.incidencias.application.consultar_incidencia import ConsultarIncidencia
    from app.incidencias.application.ports import DerivacionReader
    from app.shared.sesion import SesionActual


class ConsultarDerivacion:
    def __init__(self, derivaciones: DerivacionReader, casos: ConsultarIncidencia) -> None:
        self._derivaciones = derivaciones
        self._casos = casos

    async def execute(self, sesion: SesionActual, codigo: str) -> DerivacionDetalle:
        fila = await self._derivaciones.buscar_por_codigo(codigo)
        if fila is None:
            raise NoEncontrado(MENSAJE_DERIVACION_NO_DISPONIBLE)
        caso = await self._casos.execute(sesion, codigo, VISIBILIDAD_DE_DERIVACIONES)
        return DerivacionDetalle(resumir_derivacion(fila), caso)
