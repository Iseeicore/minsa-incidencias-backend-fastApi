from typing import TYPE_CHECKING

from sqlalchemy import text

from app.acceso.domain.sesion_vigente import SesionVigente
from app.enums.tipo_area import TipoArea
from app.shared.database import translate_database_errors
from app.shared.sesion import AreaDeSesion, VigenciaDeSesion
from app.shared.transaction import transaction

if TYPE_CHECKING:
    from sqlalchemy.engine import Row
    from sqlalchemy.ext.asyncio import AsyncEngine

CREAR = text(
    """
    INSERT INTO gestion.sesion_usuario (usuario_interno_id, vence_en)
    VALUES (CAST(:usuario_id AS uuid), now() + make_interval(hours => CAST(:horas AS int)))
    RETURNING id
    """
)
BUSCAR_VIGENTE = text(
    """
    SELECT s.id AS sesion_id,
           u.id AS usuario_id,
           u.correo,
           u.nombre_completo,
           ARRAY(
             SELECT DISTINCT r.codigo
               FROM gestion.usuario_rol ur
               JOIN gestion.rol r ON r.id = ur.rol_id AND r.activo
              WHERE ur.usuario_interno_id = u.id
              ORDER BY r.codigo
           ) AS roles,
           a.id AS area_id,
           a.codigo AS area_codigo,
           a.nombre AS area_nombre,
           ta.codigo AS area_tipo,
           (now() - s.ultima_actividad_en) > make_interval(secs => CAST(:segundos AS int)) AS debe_tocar,
           s.vence_en AS vence_en,
           s.ultima_actividad_en + make_interval(mins => CAST(:minutos AS int)) AS inactiva_en
      FROM gestion.sesion_usuario s
      JOIN gestion.usuario_interno u ON u.id = s.usuario_interno_id
      LEFT JOIN catalogo.area a ON a.id = u.area_id
      LEFT JOIN catalogo.tipo_area ta ON ta.id = a.tipo_area_id
     WHERE s.id = CAST(:sesion_id AS uuid)
       AND s.revocada_en IS NULL
       AND s.vence_en > now()
       AND s.ultima_actividad_en > now() - make_interval(mins => CAST(:minutos AS int))
       AND u.activo
    """
)
TOCAR = text(
    """
    UPDATE gestion.sesion_usuario s SET ultima_actividad_en = now()
     WHERE s.id = CAST(:sesion_id AS uuid) AND s.revocada_en IS NULL
       AND s.vence_en > now()
       AND s.ultima_actividad_en > now() - make_interval(mins => CAST(:minutos AS int))
       AND EXISTS (SELECT 1 FROM gestion.usuario_interno u WHERE u.id = s.usuario_interno_id AND u.activo)
    RETURNING s.vence_en AS vence_en,
              s.ultima_actividad_en + make_interval(mins => CAST(:minutos AS int)) AS inactiva_en
    """
)
CORREO_DE_SESION_ABIERTA = text(
    """
    SELECT u.correo
      FROM gestion.sesion_usuario s
      JOIN gestion.usuario_interno u ON u.id = s.usuario_interno_id
     WHERE s.id = CAST(:sesion_id AS uuid) AND s.revocada_en IS NULL
    """
)
REVOCAR = text(
    """
    UPDATE gestion.sesion_usuario SET revocada_en = now()
     WHERE id = CAST(:sesion_id AS uuid) AND revocada_en IS NULL
    """
)


def _area_de(fila: Row[tuple[object, ...]]) -> AreaDeSesion | None:
    if fila.area_id is None or fila.area_codigo is None or fila.area_nombre is None or fila.area_tipo is None:
        return None
    return AreaDeSesion(
        id=fila.area_id, codigo=fila.area_codigo, nombre=fila.area_nombre, tipo=TipoArea(fila.area_tipo)
    )


class SqlSesionStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def crear(self, actor: str, usuario_id: str, horas_absolutas: int) -> str:
        async with transaction(self._engine, actor) as connection:
            resultado = await connection.execute(CREAR, {"usuario_id": usuario_id, "horas": horas_absolutas})
            return str(resultado.scalar_one())

    async def buscar_vigente(
        self, sesion_id: str, minutos_inactividad: int, segundos_para_tocar: int
    ) -> SesionVigente | None:
        parametros = {"sesion_id": sesion_id, "minutos": minutos_inactividad, "segundos": segundos_para_tocar}
        with translate_database_errors():
            async with self._engine.connect() as connection:
                fila = (await connection.execute(BUSCAR_VIGENTE, parametros)).first()
        if fila is None:
            return None
        return SesionVigente(
            sesion_id=str(fila.sesion_id),
            usuario_id=str(fila.usuario_id),
            correo=fila.correo,
            nombre_completo=fila.nombre_completo,
            roles=tuple(fila.roles),
            area=_area_de(fila),
            debe_tocar=fila.debe_tocar,
            vigencia=VigenciaDeSesion(vence_en=fila.vence_en, inactiva_en=fila.inactiva_en),
        )

    async def tocar_actividad(self, actor: str, sesion_id: str, minutos_inactividad: int) -> VigenciaDeSesion | None:
        async with transaction(self._engine, actor) as connection:
            fila = (await connection.execute(TOCAR, {"sesion_id": sesion_id, "minutos": minutos_inactividad})).first()
        return None if fila is None else VigenciaDeSesion(vence_en=fila.vence_en, inactiva_en=fila.inactiva_en)

    async def revocar(self, actor: str, sesion_id: str) -> None:
        async with transaction(self._engine, actor) as connection:
            await connection.execute(REVOCAR, {"sesion_id": sesion_id})

    async def buscar_correo_de_sesion_abierta(self, sesion_id: str) -> str | None:
        with translate_database_errors():
            async with self._engine.connect() as connection:
                return (
                    await connection.execute(CORREO_DE_SESION_ABIERTA, {"sesion_id": sesion_id})
                ).scalar_one_or_none()
