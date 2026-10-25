from typing import TYPE_CHECKING

from sqlalchemy import text

from app.constants.derivaciones import ESTADOS_DE_DERIVACION
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.situacion_derivacion import SituacionDerivacion
from app.incidencias.adapters.persistence.consultas_de_derivacion import (
    columnas_de_derivacion,
    condiciones_de_derivacion,
    desde_ultimo_envio,
)
from app.incidencias.adapters.persistence.mapeo import Fila, derivacion_de
from app.incidencias.domain.derivaciones import ConteosDeDerivaciones, FiltrosDeDerivaciones
from app.shared.database import translate_database_errors
from app.shared.sql_params import ParametrosSql

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from app.incidencias.domain.derivaciones import ConsultaDeDerivaciones, DerivacionConsultada


class SqlDerivacionReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def _filas(self, sql: str, p: ParametrosSql) -> list[Fila]:
        with translate_database_errors():
            async with self._engine.connect() as connection:
                return list((await connection.execute(text(sql), p.valores)).mappings().all())

    async def listar(self, consulta: ConsultaDeDerivaciones, limite: int) -> list[DerivacionConsultada]:
        p = ParametrosSql()
        base = columnas_de_derivacion(p)
        condiciones = condiciones_de_derivacion(p, consulta.filtros, con_situacion=True)
        if consulta.despues_de is not None:
            fecha = p.con_tipo(consulta.despues_de.fecha_derivacion, "timestamptz")
            identificador = p.con_tipo(consulta.despues_de.id, "bigint")
            condiciones.append(f"(envio.fecha_hora, envio.id) < ({fecha}, {identificador})")
        sql = f"""{base}
       WHERE {" AND ".join(condiciones)}
       ORDER BY envio.fecha_hora DESC, envio.id DESC
       LIMIT {p.con_tipo(limite, "int")}"""
        return [derivacion_de(fila) for fila in await self._filas(sql, p)]

    async def contar(self, filtros: FiltrosDeDerivaciones) -> ConteosDeDerivaciones:
        p = ParametrosSql()
        base = desde_ultimo_envio(p)
        condiciones = condiciones_de_derivacion(p, filtros, con_situacion=False)
        pendientes = [estado.value for estado in ESTADOS_DE_DERIVACION[SituacionDerivacion.PENDIENTE]]
        sql = f"""SELECT (count(*))::int AS todos,
        (count(*) FILTER (WHERE e.codigo = ANY({p.con_tipo(pendientes, "text[]")})))::int AS pendientes,
        (count(*) FILTER (WHERE e.codigo = {p.agregar(EstadoIncidencia.EN_GESTION.value)}))::int AS en_gestion,
        (count(*) FILTER (WHERE e.codigo = {p.agregar(EstadoIncidencia.RESUELTO.value)}))::int AS resueltos,
        (count(*) FILTER (WHERE e.codigo = {p.agregar(EstadoIncidencia.ARCHIVADO.value)}))::int AS archivados
      {base} WHERE {" AND ".join(condiciones)}"""
        fila = (await self._filas(sql, p))[0]
        return ConteosDeDerivaciones(
            todos=fila["todos"],
            pendientes=fila["pendientes"],
            en_gestion=fila["en_gestion"],
            resueltos=fila["resueltos"],
            archivados=fila["archivados"],
        )

    async def buscar_por_codigo(self, codigo: str) -> DerivacionConsultada | None:
        p = ParametrosSql()
        base = columnas_de_derivacion(p)
        condiciones = [
            *condiciones_de_derivacion(p, FiltrosDeDerivaciones(), con_situacion=False),
            f"i.codigo = {p.agregar(codigo)}",
        ]
        filas = await self._filas(f"{base} WHERE {' AND '.join(condiciones)}", p)
        return derivacion_de(filas[0]) if filas else None
