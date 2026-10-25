from typing import TYPE_CHECKING

from app.incidencias.application.armar_derivacion import resumir_derivacion
from app.incidencias.domain.cursores import PosicionDeDerivacion, codificar_cursor_de_derivacion
from app.shared.pagination import Pagina, limite_con_extra, pagina_de

if TYPE_CHECKING:
    from app.incidencias.application.ports import DerivacionReader
    from app.incidencias.domain.derivaciones import ConsultaDeDerivaciones, DerivacionConsultada, DerivacionResumen


def _cursor_de(fila: DerivacionConsultada) -> str:
    return codificar_cursor_de_derivacion(PosicionDeDerivacion(fila.fecha_derivacion, fila.id))


class ListarDerivaciones:
    def __init__(self, derivaciones: DerivacionReader) -> None:
        self._derivaciones = derivaciones

    async def execute(self, consulta: ConsultaDeDerivaciones) -> Pagina[DerivacionResumen]:
        filas = await self._derivaciones.listar(consulta, limite_con_extra(consulta.limite))
        pagina = pagina_de(filas, consulta.limite, _cursor_de)
        return Pagina([resumir_derivacion(fila) for fila in pagina.items], pagina.siguiente, pagina.hay_mas)
