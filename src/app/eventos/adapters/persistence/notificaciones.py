from typing import TYPE_CHECKING

import psycopg
from sqlalchemy import text

from app.constants.actores import ACTOR_SISTEMA_TIEMPO_REAL
from app.constants.eventos import (
    CANAL_CAMBIOS_INCIDENCIAS,
    CLAVE_DE_BLOQUEO_DE_INSTALACION,
    DISPARADOR_DE_NOTIFICACION,
    EVENTOS_APLICACION,
    EVENTOS_TIPO_DE_DISPARADOR,
    FUNCION_DE_NOTIFICACION,
    VERSION_DE_NOTIFICACION,
)
from app.eventos.application.ports import NotificacionDeCanal
from app.shared.transaction import transaction

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine

BLOQUEAR = text("SELECT pg_advisory_xact_lock(hashtext(:clave))")
ESTA_INSTALADA = text(
    "SELECT EXISTS ("
    " SELECT 1 FROM pg_trigger t"
    " WHERE t.tgname = :disparador"
    " AND t.tgrelid = 'chatbot.incidencia_paciente'::regclass"
    " AND t.tgfoid = to_regprocedure(:funcion)"
    " AND NOT t.tgisinternal AND t.tgtype = :tipo AND t.tgenabled IN ('O', 'A')"
    " AND position(:version IN pg_get_functiondef(t.tgfoid)) > 0)"
)
SQL_DE_INSTALACION = f"""
CREATE OR REPLACE FUNCTION {FUNCION_DE_NOTIFICACION}()
RETURNS trigger
LANGUAGE plpgsql
AS $funcion$
BEGIN
  -- {VERSION_DE_NOTIFICACION}
  IF TG_OP = 'UPDATE' AND ROW(
    OLD.estado_incidencia_id, OLD.categoria_id, OLD.area_destino_id, OLD.establecimiento_id,
    OLD.activo, OLD.categoria_confirmada_en, OLD.categoria_corregida_en,
    OLD.tomado_por, OLD.tomado_en, OLD.resuelto_en, OLD.motivo_archivo_id,
    OLD.archivado_en, OLD.reabierto_en, OLD.fecha_creacion, OLD.descripcion
  ) IS NOT DISTINCT FROM ROW(
    NEW.estado_incidencia_id, NEW.categoria_id, NEW.area_destino_id, NEW.establecimiento_id,
    NEW.activo, NEW.categoria_confirmada_en, NEW.categoria_corregida_en,
    NEW.tomado_por, NEW.tomado_en, NEW.resuelto_en, NEW.motivo_archivo_id,
    NEW.archivado_en, NEW.reabierto_en, NEW.fecha_creacion, NEW.descripcion
  ) THEN
    RETURN NULL;
  END IF;
  PERFORM pg_notify('{CANAL_CAMBIOS_INCIDENCIAS}', json_build_object(
    'areaAntes', CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE OLD.area_destino_id END,
    'areaDespues', CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE NEW.area_destino_id END,
    'categoriaAntes', CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE OLD.categoria_id END,
    'categoriaDespues', CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE NEW.categoria_id END
  )::text);
  RETURN NULL;
END;
$funcion$;
DROP TRIGGER IF EXISTS {DISPARADOR_DE_NOTIFICACION} ON chatbot.incidencia_paciente;
CREATE TRIGGER {DISPARADOR_DE_NOTIFICACION}
  AFTER INSERT OR UPDATE OR DELETE ON chatbot.incidencia_paciente
  FOR EACH ROW
  EXECUTE FUNCTION {FUNCION_DE_NOTIFICACION}();
"""


class SqlInstaladorDeNotificaciones:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def instalar(self) -> None:
        async with transaction(self._engine, ACTOR_SISTEMA_TIEMPO_REAL) as conexion:
            await conexion.execute(BLOQUEAR, {"clave": CLAVE_DE_BLOQUEO_DE_INSTALACION})
            parametros = {
                "disparador": DISPARADOR_DE_NOTIFICACION,
                "funcion": f"{FUNCION_DE_NOTIFICACION}()",
                "tipo": EVENTOS_TIPO_DE_DISPARADOR,
                "version": VERSION_DE_NOTIFICACION,
            }
            if not (await conexion.execute(ESTA_INSTALADA, parametros)).scalar_one():
                await conexion.exec_driver_sql(SQL_DE_INSTALACION)


class ConexionPostgres:
    def __init__(self, conexion: psycopg.AsyncConnection) -> None:
        self._conexion = conexion

    async def notificaciones(self) -> AsyncIterator[NotificacionDeCanal]:
        async for aviso in self._conexion.notifies():
            yield NotificacionDeCanal(aviso.channel, aviso.payload or None)

    async def cerrar(self) -> None:
        await self._conexion.close()


class AbridorDeConexionPostgres:
    def __init__(self, url: str, segundos_para_conectar: int) -> None:
        self._url = url
        self._segundos_para_conectar = segundos_para_conectar

    async def abrir(self) -> ConexionPostgres:
        conexion = await psycopg.AsyncConnection.connect(
            self._url,
            autocommit=True,
            connect_timeout=self._segundos_para_conectar,
            application_name=EVENTOS_APLICACION,
        )
        try:
            await conexion.execute(f"LISTEN {CANAL_CAMBIOS_INCIDENCIAS}")
        except BaseException:
            await conexion.close()
            raise
        return ConexionPostgres(conexion)
