from typing import TYPE_CHECKING

from sqlalchemy import text

from app.acceso.domain.usuario_interno import UsuarioInterno
from app.shared.database import translate_database_errors

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

BUSCAR_POR_CORREO = text(
    """
    SELECT id, correo, nombre_completo, password_hash, activo
      FROM gestion.usuario_interno
     WHERE correo = :correo
    """
)


class SqlUsuarioFinder:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def buscar_por_correo(self, correo: str) -> UsuarioInterno | None:
        with translate_database_errors():
            async with self._engine.connect() as connection:
                fila = (await connection.execute(BUSCAR_POR_CORREO, {"correo": correo})).first()
        if fila is None:
            return None
        return UsuarioInterno(
            id=str(fila.id),
            correo=fila.correo,
            nombre_completo=fila.nombre_completo,
            password_hash=fila.password_hash,
            activo=fila.activo,
        )
