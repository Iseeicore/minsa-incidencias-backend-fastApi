from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from app.eventos.domain.cambio_de_incidencia import CategoriasPorRol

CATEGORIAS_POR_ROL = text(
    "SELECT r.codigo AS rol, rc.categoria_incidencia_id AS categoria"
    " FROM gestion.rol_categoria rc JOIN gestion.rol r ON r.id = rc.rol_id AND r.activo"
)


class SqlCategoriasPorRol:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def categorias_por_rol(self) -> CategoriasPorRol:
        async with self._engine.connect() as conexion:
            filas = (await conexion.execute(CATEGORIAS_POR_ROL)).all()
        por_rol: dict[str, set[int]] = {}
        for fila in filas:
            por_rol.setdefault(fila.rol, set()).add(fila.categoria)
        return por_rol
