from typing import TYPE_CHECKING

from app.constants.sesion import SESSION_TOUCH_INTERVAL_SECONDS
from app.shared.actor import actor_usuario_interno
from app.shared.permisos import vistas_de_roles
from app.shared.sesion import SesionActual, SesionEnVivo

if TYPE_CHECKING:
    from app.acceso.application.ports import SesionStore
    from app.acceso.domain.sesion_vigente import SesionVigente
    from app.shared.ports import ControlDeSesion, SeguimientoDeSesiones
    from app.shared.sesion import VigenciaDeSesion


class ResolverSesion:
    def __init__(
        self, sesiones: SesionStore, minutos_inactividad: int, seguimiento: SeguimientoDeSesiones | None = None
    ) -> None:
        self._sesiones = sesiones
        self._minutos_inactividad = minutos_inactividad
        self._seguimiento = seguimiento

    async def resolve(self, session_id: str) -> SesionActual | None:
        control = self._seguimiento.iniciar_verificacion(session_id) if self._seguimiento is not None else None
        try:
            sesion = await self._resolver(session_id, control)
        except BaseException:
            if control is not None:
                control.liberar()
            raise
        if sesion is None and control is not None:
            control.liberar()
        return sesion

    async def _resolver(self, session_id: str, control: ControlDeSesion | None) -> SesionActual | None:
        fila = await self._sesiones.buscar_vigente(
            session_id, self._minutos_inactividad, SESSION_TOUCH_INTERVAL_SECONDS
        )
        if fila is None:
            self._invalidar(session_id)
            return None
        if control is not None and not control.identificar(fila.usuario_id):
            return None
        vigencia = await self._vigencia_actualizada(fila)
        if vigencia is None:
            self._invalidar(session_id)
            return None
        if control is not None and not control.vigente():
            return None
        return self._autenticada(fila, vigencia, control)

    def _invalidar(self, session_id: str) -> None:
        if self._seguimiento is not None:
            self._seguimiento.invalidar_sesion(session_id)

    async def _vigencia_actualizada(self, fila: SesionVigente) -> VigenciaDeSesion | None:
        if not fila.debe_tocar:
            return fila.vigencia
        return await self._sesiones.tocar_actividad(
            actor_usuario_interno(fila.correo), fila.sesion_id, self._minutos_inactividad
        )

    def _autenticada(
        self, fila: SesionVigente, vigencia: VigenciaDeSesion, control: ControlDeSesion | None
    ) -> SesionActual:
        if control is not None and self._seguimiento is not None:
            self._seguimiento.actualizar_sesion(
                SesionEnVivo(
                    sesion_id=fila.sesion_id,
                    usuario_id=fila.usuario_id,
                    roles=fila.roles,
                    area_id=fila.area.id if fila.area is not None else None,
                    vigencia=vigencia,
                    control=control,
                )
            )
        return SesionActual(
            sesion_id=fila.sesion_id,
            usuario_id=fila.usuario_id,
            correo=fila.correo,
            nombre_completo=fila.nombre_completo,
            roles=fila.roles,
            area=fila.area,
            vistas=vistas_de_roles(fila.roles),
            vigencia=vigencia,
            control_eventos=control,
        )
