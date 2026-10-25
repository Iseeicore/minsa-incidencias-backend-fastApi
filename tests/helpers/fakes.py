from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.catalogos.domain.plazo_de_categoria import PlazoDeCategoria

AHORA_FIJA = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


class FixedClock:
    def __init__(self, ahora: datetime = AHORA_FIJA) -> None:
        self._ahora = ahora

    def now(self) -> datetime:
        return self._ahora


class StaticDatabaseProbe:
    def __init__(self, disponible: bool) -> None:  # noqa: FBT001
        self._disponible = disponible

    async def ping(self) -> bool:
        return self._disponible


class InMemoryPlazoRepository:
    def __init__(self, plazos: list[PlazoDeCategoria] | None = None) -> None:
        self._plazos = list(plazos or [])

    async def plazos_por_categoria(self) -> list[PlazoDeCategoria]:
        return list(self._plazos)


class RaisingPlazoRepository:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def plazos_por_categoria(self) -> list[PlazoDeCategoria]:
        raise self._error
