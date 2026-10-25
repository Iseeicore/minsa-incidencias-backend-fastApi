from typing import TYPE_CHECKING

from sqlalchemy import text

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.incidencias.domain.analisis import FilaAnalisis
from app.shared.database import translate_database_errors

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

BUSCAR = text(
    """
    SELECT a.version_reglas,
           CAST(a.puntaje AS int) AS puntaje,
           a.senales,
           a.cargo_mencionado,
           a.nombre_mencionado,
           ar.codigo AS area_mencionada_codigo,
           ar.nombre AS area_mencionada_nombre,
           cia.codigo AS categoria_ia,
           CAST(i.categoria_confianza AS float8) AS confianza_ia,
           i.version_clasificador,
           a.fecha_creacion AS fecha_analisis
      FROM chatbot.incidencia_analisis a
      JOIN chatbot.incidencia_paciente i ON i.id = a.incidencia_paciente_id
      LEFT JOIN catalogo.area ar ON ar.id = a.area_mencionada_id
      LEFT JOIN catalogo.categoria_incidencia cia ON cia.id = i.categoria_ia_id
     WHERE a.incidencia_paciente_id = CAST(:incidencia_id AS uuid)
    """
)


class SqlAnalisisReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def buscar(self, incidencia_id: str) -> FilaAnalisis | None:
        with translate_database_errors():
            async with self._engine.connect() as connection:
                fila = (await connection.execute(BUSCAR, {"incidencia_id": incidencia_id})).first()
        if fila is None:
            return None
        return FilaAnalisis(
            version_reglas=fila.version_reglas,
            puntaje=fila.puntaje,
            senales=fila.senales,
            cargo_mencionado=fila.cargo_mencionado,
            nombre_mencionado=fila.nombre_mencionado,
            area_mencionada_codigo=fila.area_mencionada_codigo,
            area_mencionada_nombre=fila.area_mencionada_nombre,
            categoria_ia=CategoriaIncidencia(fila.categoria_ia) if fila.categoria_ia is not None else None,
            confianza_ia=fila.confianza_ia,
            version_clasificador=fila.version_clasificador,
            fecha_analisis=fila.fecha_analisis,
        )
