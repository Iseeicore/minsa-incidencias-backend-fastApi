from typing import TYPE_CHECKING

from sqlalchemy import text

from app.catalogos.domain.area_listada import AreaListada, EstablecimientoDeArea
from app.catalogos.domain.codigo_renipress import codigo_renipress_buscado
from app.enums.tipo_area import TipoArea
from app.shared.database import translate_database_errors
from app.shared.text_search import like_pattern

if TYPE_CHECKING:
    from sqlalchemy.engine import Row
    from sqlalchemy.ext.asyncio import AsyncEngine

    from app.catalogos.domain.area_listada import FiltrosDeAreas
    from app.shared.cursor import PosicionPorNombre

LISTAR = text(
    r"""
    SELECT a.id,
           a.codigo,
           a.nombre,
           ta.codigo AS tipo_area,
           es.codigo_renipress,
           na.codigo AS nivel_atencion,
           es.categoria
      FROM catalogo.area a
      JOIN catalogo.tipo_area ta ON ta.id = a.tipo_area_id
      LEFT JOIN catalogo.establecimiento_salud es ON es.area_id = a.id
      LEFT JOIN catalogo.nivel_atencion na ON na.id = es.nivel_atencion_id
     WHERE a.activo AND ta.activo
       AND (NOT :restringir OR a.id = CAST(:solo_area_id AS int))
       AND (CAST(:tipo AS text) IS NULL OR ta.codigo = CAST(:tipo AS text))
       AND (CAST(:patron AS text) IS NULL
            OR COALESCE(es.nombre_busqueda, public.f_unaccent(a.nombre))
               LIKE public.f_unaccent(CAST(:patron AS text)) ESCAPE '\'
            OR (CAST(:renipress AS text) IS NOT NULL AND es.codigo_renipress = CAST(:renipress AS text)))
       AND (NOT :hay_cursor OR (a.nombre, a.id) > (CAST(:cursor_nombre AS text), CAST(:cursor_id AS int)))
     ORDER BY a.nombre, a.id
     LIMIT :limite
    """
)


def _area_de(fila: Row[tuple[object, ...]]) -> AreaListada:
    establecimiento = (
        EstablecimientoDeArea(fila.codigo_renipress, fila.nivel_atencion, fila.categoria)
        if fila.codigo_renipress
        else None
    )
    return AreaListada(
        id=fila.id,
        codigo=fila.codigo,
        nombre=fila.nombre,
        tipo_area=TipoArea(fila.tipo_area),
        establecimiento=establecimiento,
    )


class SqlAreaFinder:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def listar(
        self, filtros: FiltrosDeAreas, limite: int, despues_de: PosicionPorNombre[int] | None
    ) -> list[AreaListada]:
        parametros = {
            "restringir": filtros.restringir_a_un_area,
            "solo_area_id": filtros.solo_area_id,
            "tipo": filtros.tipo.value if filtros.tipo is not None else None,
            "patron": like_pattern(filtros.texto),
            "renipress": codigo_renipress_buscado(filtros.texto) if filtros.texto else None,
            "hay_cursor": despues_de is not None,
            "cursor_nombre": despues_de.nombre if despues_de is not None else None,
            "cursor_id": despues_de.id if despues_de is not None else None,
            "limite": limite,
        }
        with translate_database_errors():
            async with self._engine.connect() as connection:
                filas = (await connection.execute(LISTAR, parametros)).all()
        return [_area_de(fila) for fila in filas]
