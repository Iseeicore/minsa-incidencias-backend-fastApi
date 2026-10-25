from typing import TYPE_CHECKING

from app.shared.actor import actor_usuario_interno

if TYPE_CHECKING:
    from app.acceso.application.ports import SesionStore
    from app.shared.ports import SeguimientoDeSesiones
    from app.shared.sesion import SesionActual


class CerrarSesion:
    def __init__(self, sesiones: SesionStore, seguimiento: SeguimientoDeSesiones | None = None) -> None:
        self._sesiones = sesiones
        self._seguimiento = seguimiento

    async def de_la_sesion(self, sesion: SesionActual) -> None:
        await self._sesiones.revocar(actor_usuario_interno(sesion.correo), sesion.sesion_id)
        self._invalidar(sesion.sesion_id)

    async def por_id(self, sesion_id: str) -> None:
        correo = await self._sesiones.buscar_correo_de_sesion_abierta(sesion_id)
        if correo is not None:
            await self._sesiones.revocar(actor_usuario_interno(correo), sesion_id)
        self._invalidar(sesion_id)

    def _invalidar(self, sesion_id: str) -> None:
        if self._seguimiento is not None:
            self._seguimiento.invalidar_sesion(sesion_id)
