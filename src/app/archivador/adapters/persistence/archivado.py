from typing import TYPE_CHECKING

from sqlalchemy import text

from app.constants.actores import ACTOR_SISTEMA_ARCHIVADOR
from app.constants.archivado import CANDADO_DEL_ARCHIVADOR
from app.shared.transaction import transaction

if TYPE_CHECKING:
    from sqlalchemy import TextClause
    from sqlalchemy.ext.asyncio import AsyncEngine

TOMAR_CANDADO = text("SELECT pg_try_advisory_xact_lock(:clave)")
ARCHIVAR_VENCIDAS = text("SELECT CAST(chatbot.archivar_incidencias_vencidas(p_lote => CAST(:lote AS int)) AS int)")
ARCHIVAR_RESUELTAS = text(
    "SELECT CAST(chatbot.archivar_incidencias_resueltas(CAST(:dias AS int), CAST(:lote AS int)) AS int)"
)


class SqlArchivadoRepositorio:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def archivar_vencidas(self, lote: int) -> int:
        return await self._ejecutar(ARCHIVAR_VENCIDAS, lote=lote)

    async def archivar_resueltas(self, dias: int, lote: int) -> int:
        return await self._ejecutar(ARCHIVAR_RESUELTAS, dias=dias, lote=lote)

    async def _ejecutar(self, sentencia: TextClause, **parametros: object) -> int:
        async with transaction(self._engine, ACTOR_SISTEMA_ARCHIVADOR) as conexion:
            if not (await conexion.execute(TOMAR_CANDADO, {"clave": CANDADO_DEL_ARCHIVADOR})).scalar_one():
                return 0
            return int((await conexion.execute(sentencia, parametros)).scalar_one())
