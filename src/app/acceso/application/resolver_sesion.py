from typing import TYPE_CHECKING

from app.constants.sesion import SESSION_TOUCH_INTERVAL_SECONDS
from app.shared.actor import actor_usuario_interno
from app.shared.permisos import vistas_de_roles
from app.shared.sesion import SesionActual

if TYPE_CHECKING:
    from app.acceso.application.ports import SesionStore
    from app.shared.sesion import VigenciaDeSesion


class ResolverSesion:
    def __init__(self, sesiones: SesionStore, minutos_inactividad: int) -> None:
        self._sesiones = sesiones
        self._minutos_inactividad = minutos_inactividad

    async def resolve(self, session_id: str) -> SesionActual | None:
        fila = await self._sesiones.buscar_vigente(
            session_id, self._minutos_inactividad, SESSION_TOUCH_INTERVAL_SECONDS
        )
        if fila is None:
            return None
        vigencia: VigenciaDeSesion | None = fila.vigencia
        if fila.debe_tocar:
            vigencia = await self._sesiones.tocar_actividad(
                actor_usuario_interno(fila.correo), fila.sesion_id, self._minutos_inactividad
            )
        if vigencia is None:
            return None
        return SesionActual(
            sesion_id=fila.sesion_id,
            usuario_id=fila.usuario_id,
            correo=fila.correo,
            nombre_completo=fila.nombre_completo,
            roles=fila.roles,
            area=fila.area,
            vistas=vistas_de_roles(fila.roles),
            vigencia=vigencia,
        )
