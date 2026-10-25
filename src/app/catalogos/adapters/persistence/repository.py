from typing import TYPE_CHECKING

from sqlalchemy import select

from app.catalogos.adapters.persistence.tables import categoria_incidencia_table as categoria
from app.catalogos.domain.plazo_de_categoria import PlazoDeCategoria
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.shared.database import translate_database_errors

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


class SqlPlazoRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def plazos_por_categoria(self) -> list[PlazoDeCategoria]:
        consulta = (
            select(categoria.c.codigo, categoria.c.plazo_dias_habiles, categoria.c.archiva_por_vencimiento)
            .where(categoria.c.activo, categoria.c.codigo.in_([valor.value for valor in CategoriaIncidencia]))
            .order_by(categoria.c.id)
        )
        with translate_database_errors():
            async with self._engine.connect() as connection:
                filas = (await connection.execute(consulta)).all()
        return [
            PlazoDeCategoria(
                categoria=CategoriaIncidencia(fila.codigo),
                plazo_dias_habiles=fila.plazo_dias_habiles,
                archiva_por_vencimiento=fila.archiva_por_vencimiento,
            )
            for fila in filas
        ]
