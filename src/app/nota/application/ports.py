from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.nota.domain.codigo_nota import CodigoNota
    from app.nota.domain.nota import Nota


class NotaWriter(Protocol):
    async def save(self, nota: Nota) -> None: ...


class NotaFinder(Protocol):
    async def find_by_codigo(self, codigo: CodigoNota) -> Nota | None: ...


class CodeGenerator(Protocol):
    async def next_codigo(self) -> CodigoNota: ...
