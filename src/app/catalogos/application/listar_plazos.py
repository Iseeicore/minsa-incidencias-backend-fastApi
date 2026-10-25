from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.catalogos.application.ports import PlazoFinder
    from app.catalogos.domain.plazo_de_categoria import PlazoDeCategoria


class ListarPlazos:
    def __init__(self, plazos: PlazoFinder) -> None:
        self._plazos = plazos

    async def execute(self) -> list[PlazoDeCategoria]:
        return await self._plazos.plazos_por_categoria()
