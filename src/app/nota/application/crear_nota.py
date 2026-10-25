from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.nota.domain.nota import Nota

if TYPE_CHECKING:
    from app.nota.application.ports import CodeGenerator, NotaWriter
    from app.shared.clock import Clock


@dataclass(frozen=True, slots=True)
class CrearNotaComando:
    titulo: str
    contenido: str


class CrearNota:
    def __init__(self, notas: NotaWriter, codigos: CodeGenerator, clock: Clock) -> None:
        self._notas = notas
        self._codigos = codigos
        self._clock = clock

    async def execute(self, comando: CrearNotaComando) -> Nota:
        nota = Nota.crear(await self._codigos.next_codigo(), comando.titulo, comando.contenido, self._clock.now())
        await self._notas.save(nota)
        return nota
