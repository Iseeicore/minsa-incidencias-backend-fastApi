from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.catalogos.domain.plazo_de_categoria import PlazoDeCategoria


class PlazoFinder(Protocol):
    async def plazos_por_categoria(self) -> list[PlazoDeCategoria]: ...
