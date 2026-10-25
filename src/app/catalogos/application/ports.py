from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.catalogos.domain.area_listada import AreaListada, FiltrosDeAreas
    from app.catalogos.domain.plazo_de_categoria import PlazoDeCategoria
    from app.shared.cursor import PosicionPorNombre


class PlazoFinder(Protocol):
    async def plazos_por_categoria(self) -> list[PlazoDeCategoria]: ...


class AreaFinder(Protocol):
    async def listar(
        self, filtros: FiltrosDeAreas, limite: int, despues_de: PosicionPorNombre[int] | None
    ) -> list[AreaListada]: ...
