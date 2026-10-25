from typing import TYPE_CHECKING

from sqlalchemy import text

from app.enums.tipo_area import TipoArea
from app.incidencias.domain.ipress import IpressConsultada, IpressListada
from app.shared.codigo_renipress import codigo_renipress_buscado
from app.shared.database import translate_database_errors
from app.shared.text_search import like_pattern

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from app.incidencias.domain.ipress import ConsultaDeIpress

BUSCAR = text(
    """
    SELECT es.id AS establecimiento_id, a.codigo, a.nombre
      FROM catalogo.establecimiento_salud es
      JOIN catalogo.area a ON a.id = es.area_id AND a.activo
      JOIN catalogo.tipo_area ta ON ta.id = a.tipo_area_id AND ta.activo AND ta.codigo = :tipo
     WHERE es.activo AND es.codigo_renipress = :renipress
    """
)

LISTAR = text(
    r"""
    SELECT a.id,
           a.codigo,
           a.nombre,
           es.codigo_renipress,
           na.codigo AS nivel_atencion,
           es.categoria
      FROM catalogo.area a
      JOIN catalogo.tipo_area ta ON ta.id = a.tipo_area_id
      LEFT JOIN catalogo.establecimiento_salud es ON es.area_id = a.id
      LEFT JOIN catalogo.nivel_atencion na ON na.id = es.nivel_atencion_id
     WHERE a.activo AND ta.activo AND es.activo
       AND ta.codigo = :tipo
       AND (CAST(:patron AS text) IS NULL
            OR COALESCE(es.nombre_busqueda, public.f_unaccent(a.nombre))
               LIKE public.f_unaccent(CAST(:patron AS text)) ESCAPE '\'
            OR (CAST(:renipress AS text) IS NOT NULL AND es.codigo_renipress = CAST(:renipress AS text)))
       AND (NOT :hay_cursor OR (a.nombre, a.id) > (CAST(:cursor_nombre AS text), CAST(:cursor_id AS int)))
     ORDER BY a.nombre, a.id
     LIMIT :limite
    """
)


class SqlIpressFinder:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def buscar(self, renipress: str) -> IpressConsultada | None:
        parametros = {"tipo": TipoArea.ESTABLECIMIENTO.value, "renipress": renipress}
        with translate_database_errors():
            async with self._engine.connect() as connection:
                fila = (await connection.execute(BUSCAR, parametros)).first()
        return IpressConsultada(fila.establecimiento_id, fila.codigo, fila.nombre) if fila is not None else None

    async def listar(self, consulta: ConsultaDeIpress, limite: int) -> list[IpressListada]:
        despues_de = consulta.despues_de
        parametros = {
            "tipo": TipoArea.ESTABLECIMIENTO.value,
            "patron": like_pattern(consulta.texto),
            "renipress": codigo_renipress_buscado(consulta.texto) if consulta.texto else None,
            "hay_cursor": despues_de is not None,
            "cursor_nombre": despues_de.nombre if despues_de is not None else None,
            "cursor_id": despues_de.id if despues_de is not None else None,
            "limite": limite,
        }
        with translate_database_errors():
            async with self._engine.connect() as connection:
                filas = (await connection.execute(LISTAR, parametros)).all()
        return [
            IpressListada(
                id=fila.id,
                codigo=fila.codigo,
                nombre=fila.nombre,
                codigo_renipress=fila.codigo_renipress,
                nivel_atencion=fila.nivel_atencion,
                categoria=fila.categoria,
            )
            for fila in filas
        ]
