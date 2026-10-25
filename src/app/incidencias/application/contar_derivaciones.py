from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.incidencias.application.ports import DerivacionReader
    from app.incidencias.domain.derivaciones import ConteosDeDerivaciones, FiltrosDeDerivaciones


class ContarDerivaciones:
    def __init__(self, derivaciones: DerivacionReader) -> None:
        self._derivaciones = derivaciones

    async def execute(self, filtros: FiltrosDeDerivaciones) -> ConteosDeDerivaciones:
        return await self._derivaciones.contar(replace(filtros, situacion=None))
