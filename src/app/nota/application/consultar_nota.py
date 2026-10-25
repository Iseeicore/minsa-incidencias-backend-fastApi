from typing import TYPE_CHECKING

from app.nota.domain.codigo_nota import CodigoNota
from app.nota.domain.errors.nota_no_encontrada import NotaNoEncontrada

if TYPE_CHECKING:
    from app.nota.application.ports import NotaFinder
    from app.nota.domain.nota import Nota


class ConsultarNota:
    def __init__(self, notas: NotaFinder) -> None:
        self._notas = notas

    async def execute(self, codigo: str) -> Nota:
        nota = await self._notas.find_by_codigo(CodigoNota(codigo))
        if nota is None:
            raise NotaNoEncontrada(codigo)
        return nota
