from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.nota.domain.codigo_nota import CodigoNota

if TYPE_CHECKING:
    from app.nota.domain.nota import Nota

AHORA_FIJA = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


class FixedClock:
    def __init__(self, ahora: datetime = AHORA_FIJA) -> None:
        self._ahora = ahora

    def now(self) -> datetime:
        return self._ahora


class SequentialCodeGenerator:
    def __init__(self, siguiente: int = 1) -> None:
        self._siguiente = siguiente

    async def next_codigo(self) -> CodigoNota:
        codigo = CodigoNota.desde_numero(self._siguiente)
        self._siguiente += 1
        return codigo


class RaisingNotaRepository:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def save(self, nota: Nota) -> None:  # noqa: ARG002
        raise self._error

    async def find_by_codigo(self, codigo: CodigoNota) -> Nota | None:  # noqa: ARG002
        raise self._error


class StaticDatabaseProbe:
    def __init__(self, disponible: bool) -> None:  # noqa: FBT001
        self._disponible = disponible

    async def ping(self) -> bool:
        return self._disponible


class InMemoryNotaRepository:
    def __init__(self, notas: list[Nota] | None = None) -> None:
        self._notas = {nota.codigo: nota for nota in notas or []}

    async def save(self, nota: Nota) -> None:
        self._notas[nota.codigo] = nota

    async def find_by_codigo(self, codigo: CodigoNota) -> Nota | None:
        return self._notas.get(codigo)
