from typing import TYPE_CHECKING

from sqlalchemy import text

from app.constants.incidencias import ACTOR_PREFIJO_USUARIO
from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.adapters.persistence import consultas, sentencias
from app.incidencias.adapters.persistence.mapeo import Fila, caso_de, fila_de_historial
from app.incidencias.application.filtros import sin_estado_ni_motivo
from app.incidencias.domain.caso_consultado import ConteoPorVencer, EvidenciaConsultada
from app.incidencias.domain.imagen_de_evidencia import INICIO_DE_IMAGEN_PERMITIDA
from app.shared.database import translate_database_errors
from app.shared.sql_params import ParametrosSql

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from app.incidencias.domain.caso_consultado import CasoConsultado
    from app.incidencias.domain.consultas import FiltrosCasos, Visibilidad
    from app.incidencias.domain.cursores import PosicionDeListado, PosicionPorVencer
    from app.incidencias.domain.fila_historial import FilaHistorial
    from app.shared.permisos import ReglaDeAccion


class SqlIncidenciaReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def _filas(self, sql: str, p: ParametrosSql) -> list[Fila]:
        with translate_database_errors():
            async with self._engine.connect() as connection:
                return list((await connection.execute(text(sql), p.valores)).mappings().all())

    async def listar(
        self,
        visible: Visibilidad,
        filtros: FiltrosCasos,
        limite: int,
        despues_de: PosicionDeListado | None,
    ) -> list[CasoConsultado]:
        p = ParametrosSql()
        base = consultas.consulta_de_caso(p)
        condiciones = [*consultas.condiciones_base(p, visible), *consultas.condiciones_de_filtros(p, filtros)]
        if despues_de is not None:
            fecha = p.con_tipo(despues_de.fecha_creacion, "timestamptz")
            identificador = p.con_tipo(despues_de.id, "uuid")
            condiciones.append(f"(i.fecha_creacion, i.id) < ({fecha}, {identificador})")
        sql = f"""{base}
       WHERE {" AND ".join(condiciones)}
       ORDER BY i.fecha_creacion DESC, i.id DESC
       LIMIT {p.con_tipo(limite, "int")}"""
        return [caso_de(fila) for fila in await self._filas(sql, p)]

    async def listar_proximos_a_vencer(
        self,
        visible: Visibilidad,
        filtros: FiltrosCasos,
        limite: int,
        despues_de: PosicionPorVencer | None,
    ) -> list[CasoConsultado]:
        p = ParametrosSql()
        base = consultas.consulta_de_caso(p)
        condiciones = [*consultas.condiciones_base(p, visible), *consultas.condiciones_de_filtros(p, filtros)]
        if despues_de is not None:
            vence = p.con_tipo(despues_de.vence_en, "timestamptz")
            identificador = p.con_tipo(despues_de.id, "uuid")
            condiciones.append(f"({consultas.VENCE_LA_ATENCION_EN_MS}, i.id) > ({vence}, {identificador})")
        sql = f"""{base}
       WHERE {" AND ".join(condiciones)}
       ORDER BY {consultas.VENCE_LA_ATENCION_EN_MS} ASC, i.id ASC
       LIMIT {p.con_tipo(limite, "int")}"""
        return [caso_de(fila) for fila in await self._filas(sql, p)]

    async def contar_acotado(self, visible: Visibilidad, filtros: FiltrosCasos, tope: int) -> int:
        p = ParametrosSql()
        condiciones = [*consultas.condiciones_base(p, visible), *consultas.condiciones_de_filtros(p, filtros)]
        sql = f"""SELECT count(*)::int AS cantidad
         FROM (SELECT 1 {consultas.DESDE_BASICO}
                WHERE {" AND ".join(condiciones)}
                LIMIT {p.con_tipo(tope + 1, "int")}) s"""
        filas = await self._filas(sql, p)
        return int(filas[0]["cantidad"]) if filas else 0

    async def contar_por_estado(
        self, visible: Visibilidad, filtros: FiltrosCasos, tope: int
    ) -> dict[EstadoIncidencia, int]:
        p = ParametrosSql()
        condiciones = [
            *consultas.condiciones_base(p, visible),
            *consultas.condiciones_de_filtros(p, sin_estado_ni_motivo(filtros)),
        ]
        sql = f"""SELECT e.codigo AS estado, n.cantidad
         FROM catalogo.estado_incidencia e
        CROSS JOIN LATERAL (
          SELECT count(*)::int AS cantidad
            FROM (SELECT 1
                    FROM chatbot.incidencia_paciente i
                    LEFT JOIN catalogo.categoria_incidencia c ON c.id = i.categoria_id
                   WHERE i.estado_incidencia_id = e.id AND {" AND ".join(condiciones)}
                   LIMIT {p.con_tipo(tope + 1, "int")}) s
        ) n"""
        return {
            EstadoIncidencia(fila["estado"]): int(fila["cantidad"])
            for fila in await self._filas(sql, p)
            if fila["estado"] in EstadoIncidencia
        }

    async def buscar_por_codigo(self, codigo: str, visible: Visibilidad) -> CasoConsultado | None:
        p = ParametrosSql()
        base = consultas.consulta_de_caso(p)
        condiciones = [*consultas.condiciones_base(p, visible), f"i.codigo = {p.agregar(codigo)}"]
        sql = f"{base} WHERE {' AND '.join(condiciones)}"
        filas = await self._filas(sql, p)
        return caso_de(filas[0]) if filas else None

    async def evidencias(self, incidencia_id: str) -> list[EvidenciaConsultada]:
        parametros = {"incidencia_id": incidencia_id, "inicio": INICIO_DE_IMAGEN_PERMITIDA}
        with translate_database_errors():
            async with self._engine.connect() as connection:
                filas = (await connection.execute(sentencias.EVIDENCIAS, parametros)).mappings().all()
        return [
            EvidenciaConsultada(
                id=str(fila["id"]),
                nombre=fila["nombre"],
                tipo=fila["tipo"],
                tipo_nombre=fila["tipo_nombre"],
                fecha=fila["fecha"],
                verificada=fila["verificada"],
                contenido_disponible=fila["contenido_disponible"],
            )
            for fila in filas
        ]

    async def ruta_de_evidencia(self, incidencia_id: str, evidencia_id: str) -> str | None:
        parametros = {"incidencia_id": incidencia_id, "evidencia_id": evidencia_id}
        with translate_database_errors():
            async with self._engine.connect() as connection:
                return (await connection.execute(sentencias.RUTA_DE_EVIDENCIA, parametros)).scalar_one_or_none()

    async def historial(self, incidencia_id: str) -> list[FilaHistorial]:
        parametros = {"incidencia_id": incidencia_id, "prefijo": ACTOR_PREFIJO_USUARIO}
        with translate_database_errors():
            async with self._engine.connect() as connection:
                filas = (await connection.execute(sentencias.HISTORIAL, parametros)).mappings().all()
        return [fila_de_historial(fila) for fila in filas]

    async def contar_por_vencer(
        self, visible: Visibilidad, aviso_horas: int, pendientes: tuple[ReglaDeAccion, ...] | None
    ) -> ConteoPorVencer:
        p = ParametrosSql()
        condiciones = [
            *consultas.condiciones_base(p, visible),
            *consultas.condiciones_por_vencer(p, aviso_horas),
            *consultas.condicion_de_pendientes(p, pendientes),
        ]
        sql = f"""SELECT count(*)::int AS total,
              (count(*) FILTER (WHERE {consultas.VENCE_LA_ATENCION} <= now()))::int AS vencidos
         {consultas.DESDE_BASICO}
        WHERE {" AND ".join(condiciones)}"""
        filas = await self._filas(sql, p)
        return ConteoPorVencer(int(filas[0]["total"]), int(filas[0]["vencidos"])) if filas else ConteoPorVencer(0, 0)

    async def listar_por_vencer(
        self,
        visible: Visibilidad,
        aviso_horas: int,
        limite: int,
        pendientes: tuple[ReglaDeAccion, ...] | None,
    ) -> list[CasoConsultado]:
        p = ParametrosSql()
        base = consultas.consulta_de_caso(p)
        condiciones = [
            *consultas.condiciones_base(p, visible),
            *consultas.condiciones_por_vencer(p, aviso_horas),
            *consultas.condicion_de_pendientes(p, pendientes),
        ]
        sql = f"""{base}
       WHERE {" AND ".join(condiciones)}
       ORDER BY {consultas.VENCE_LA_ATENCION} ASC, i.codigo ASC
       LIMIT {p.con_tipo(limite, "int")}"""
        return [caso_de(fila) for fila in await self._filas(sql, p)]
