from typing import TYPE_CHECKING

from sqlalchemy import text

from app.constants.incidencias import ZONA_DE_LIMA
from app.constants.indicadores import FORMATO_DE_DIA_SQL, PERIODOS_INCLUIDOS_EN_COMPARACION
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.adapters.persistence import consultas
from app.incidencias.domain.cubos_de_evolucion import DiaDeEvolucion
from app.incidencias.domain.indicadores import FilaDistribucion, FilaResumen
from app.shared.database import translate_database_errors
from app.shared.sql_params import ParametrosSql

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.ext.asyncio import AsyncEngine

    from app.incidencias.adapters.persistence.mapeo import Fila
    from app.incidencias.domain.consultas import Visibilidad

HOY_EN_LIMA = f"(now() AT TIME ZONE '{ZONA_DE_LIMA}')::date"


def medianoche_de_hace(dias: str) -> str:
    return f"({HOY_EN_LIMA} - {dias})::timestamp AT TIME ZONE '{ZONA_DE_LIMA}'"


def _contar(condicion: str) -> str:
    return f"(count(*) FILTER (WHERE {condicion}))::int"


def _en_el_periodo(columna: str, inicio: str) -> str:
    return f"{columna} >= {inicio}"


def _en_el_anterior(columna: str, inicio_anterior: str, inicio: str) -> str:
    return f"{columna} >= {inicio_anterior} AND {columna} < {inicio}"


def consulta_de_resumen(p: ParametrosSql, visible: Visibilidad, dias: int, aviso_horas: int) -> str:
    condiciones = consultas.condiciones_base(p, visible)
    inicio = medianoche_de_hace(p.con_tipo(dias - 1, "int"))
    inicio_anterior = medianoche_de_hace(p.con_tipo(PERIODOS_INCLUIDOS_EN_COMPARACION * dias - 1, "int"))
    abierto = f"e.codigo = ANY({p.con_tipo(consultas.ESTADOS_ABIERTOS_VALORES, 'text[]')})"
    aviso = f"make_interval(hours => {p.con_tipo(aviso_horas, 'int')})"
    vence = consultas.VENCE_LA_ATENCION
    en_gestion = p.agregar(EstadoIncidencia.EN_GESTION.value)
    clasificado = p.agregar(EstadoIncidencia.CLASIFICADO.value)
    derivado = p.agregar(EstadoIncidencia.DERIVADO.value)
    corrupcion = p.agregar(CategoriaIncidencia.DENUNCIA_CORRUPCION.value)
    sin_revisar = "i.categoria_corregida_en IS NULL AND i.categoria_confirmada_en IS NULL"
    corregida = "i.categoria_corregida_en"
    return f"""SELECT now() AS generado_en,
              {_contar(_en_el_periodo("i.fecha_creacion", inicio))} AS recibidos,
              {_contar(_en_el_anterior("i.fecha_creacion", inicio_anterior, inicio))} AS recibidos_anterior,
              {_contar(abierto)} AS pendientes,
              {_contar(f"e.codigo = {en_gestion}")} AS en_gestion,
              {_contar(f"{abierto} AND {vence} > now() AND {vence} <= now() + {aviso}")} AS por_vencer,
              {_contar(f"{abierto} AND {vence} <= now()")} AS vencidos,
              {_contar(_en_el_periodo("i.resuelto_en", inicio))} AS resueltos,
              {_contar(_en_el_anterior("i.resuelto_en", inicio_anterior, inicio))} AS resueltos_anterior,
              {_contar("i.categoria_id IS NULL")} AS sin_clasificar,
              {_contar(f"e.codigo = {clasificado} AND {sin_revisar}")} AS por_revisar,
              {_contar(f"e.codigo = {derivado}")} AS sin_tomar,
              {_contar(f"c.codigo = {corrupcion} AND {_en_el_periodo(corregida, inicio)}")}
                AS corregidas_a_corrupcion,
              {_contar(f"c.codigo = {corrupcion} AND {_en_el_anterior(corregida, inicio_anterior, inicio)}")}
                AS corregidas_a_corrupcion_anterior,
              (avg(extract(epoch FROM i.resuelto_en - i.fecha_creacion))
                 FILTER (WHERE {_en_el_periodo("i.resuelto_en", inicio)}))::float8 AS segundos_promedio_de_resolucion
         {consultas.DESDE_BASICO}
        WHERE {" AND ".join(condiciones)}"""


def consulta_de_evolucion(p: ParametrosSql, visible: Visibilidad, dias: int) -> str:
    condiciones = consultas.condiciones_base(p, visible)
    primer_dia = p.con_tipo(dias - 1, "int")
    inicio = medianoche_de_hace(primer_dia)
    formato = p.con_tipo(FORMATO_DE_DIA_SQL, "text")

    def del_dia(columna: str) -> str:
        return f"{columna} >= d.desde AND {columna} < d.hasta"

    return f"""SELECT to_char(d.dia, {formato}) AS dia,
              {_contar(del_dia("v.fecha_creacion"))} AS recibidos,
              {_contar(del_dia("v.resuelto_en"))} AS resueltos
         FROM (SELECT CAST(g AS date) AS dia,
                      g AT TIME ZONE '{ZONA_DE_LIMA}' AS desde,
                      (g + interval '1 day') AT TIME ZONE '{ZONA_DE_LIMA}' AS hasta
                 FROM generate_series(({HOY_EN_LIMA} - {primer_dia})::timestamp, {HOY_EN_LIMA}::timestamp,
                                      interval '1 day') g) d
         LEFT JOIN (SELECT i.fecha_creacion, i.resuelto_en
                      {consultas.DESDE_BASICO}
                     WHERE {" AND ".join(condiciones)}
                       AND (i.fecha_creacion >= {inicio} OR i.resuelto_en >= {inicio})) v
                ON ({del_dia("v.fecha_creacion")}) OR ({del_dia("v.resuelto_en")})
        GROUP BY d.dia
        ORDER BY d.dia"""


def _resumen_de(fila: Fila) -> FilaResumen:
    return FilaResumen(**{campo: fila[campo] for campo in FilaResumen.__slots__})


class SqlIndicadoresReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def _filas(self, armar: Callable[[ParametrosSql], str]) -> list[Fila]:
        p = ParametrosSql()
        sql = armar(p)
        with translate_database_errors():
            async with self._engine.connect() as connection:
                return list((await connection.execute(text(sql), p.valores)).mappings().all())

    async def resumen(self, visible: Visibilidad, dias: int, aviso_horas: int) -> FilaResumen:
        filas = await self._filas(lambda p: consulta_de_resumen(p, visible, dias, aviso_horas))
        return _resumen_de(filas[0])

    async def distribucion(self, visible: Visibilidad) -> list[FilaDistribucion]:
        def armar(p: ParametrosSql) -> str:
            return f"""SELECT e.codigo AS estado, c.codigo AS categoria, (count(*))::int AS cantidad
         {consultas.DESDE_BASICO}
        WHERE {" AND ".join(consultas.condiciones_base(p, visible))}
        GROUP BY e.codigo, c.codigo"""

        return [
            FilaDistribucion(
                EstadoIncidencia(fila["estado"]),
                CategoriaIncidencia(fila["categoria"]) if fila["categoria"] is not None else None,
                fila["cantidad"],
            )
            for fila in await self._filas(armar)
        ]

    async def evolucion_diaria(self, visible: Visibilidad, dias: int) -> list[DiaDeEvolucion]:
        filas = await self._filas(lambda p: consulta_de_evolucion(p, visible, dias))
        return [DiaDeEvolucion(fila["dia"], fila["recibidos"], fila["resueltos"]) for fila in filas]
