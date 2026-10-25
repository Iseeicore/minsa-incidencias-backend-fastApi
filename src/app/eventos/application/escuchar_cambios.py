import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

from app.constants.eventos import CANAL_CAMBIOS_INCIDENCIAS, EVENTOS_REINTENTO_SEGUNDOS
from app.constants.textos.eventos import (
    EVENTO_CIERRE_FALLIDO,
    EVENTO_ESCUCHA_PERDIDA,
    EVENTO_ESCUCHANDO,
    EVENTO_NOTIFICACION_DESCARTADA,
)
from app.errors.conexion_perdida import ConexionPerdida
from app.eventos.domain.leer_cambio import leer_cambio

if TYPE_CHECKING:
    from app.eventos.application.ports import (
        AbridorDeConexion,
        ConexionDeNotificaciones,
        InstaladorDeNotificaciones,
        NotificacionDeCanal,
    )
    from app.eventos.application.publicar_cambios import PublicarCambios
    from app.shared.ports import RegistroDeProcesos


class EscucharCambios:
    def __init__(
        self,
        instalador: InstaladorDeNotificaciones,
        abridor: AbridorDeConexion,
        publicar: PublicarCambios,
        registro: RegistroDeProcesos,
        reintento_segundos: float = EVENTOS_REINTENTO_SEGUNDOS,
    ) -> None:
        self._instalador = instalador
        self._abridor = abridor
        self._publicar = publicar
        self._registro = registro
        self._reintento_segundos = reintento_segundos
        self._tarea: asyncio.Task[None] | None = None
        self._publicaciones: set[asyncio.Task[None]] = set()
        self._reconciliar_al_volver = False

    async def iniciar(self) -> None:
        if self._tarea is not None:
            return
        await self._instalador.instalar()
        self._tarea = asyncio.create_task(self._escuchar())

    async def detener(self) -> None:
        if self._tarea is not None:
            self._tarea.cancel()
            with suppress(asyncio.CancelledError):
                await self._tarea
            self._tarea = None

    async def _escuchar(self) -> None:
        while True:
            try:
                await self._sesion_de_escucha()
            except Exception as error:  # noqa: BLE001
                self._reconciliar_al_volver = True
                self._registro.warning(EVENTO_ESCUCHA_PERDIDA, error=type(error).__name__)
            await asyncio.sleep(self._reintento_segundos)

    async def _sesion_de_escucha(self) -> None:
        conexion = await self._abridor.abrir()
        try:
            self._registro.info(EVENTO_ESCUCHANDO)
            if self._reconciliar_al_volver:
                self._reconciliar_al_volver = False
                self._publicar.publicar_cambio()
            async for notificacion in conexion.notificaciones():
                self._procesar(notificacion)
        finally:
            await self._cerrar(conexion)
        raise ConexionPerdida

    async def _cerrar(self, conexion: ConexionDeNotificaciones) -> None:
        try:
            await asyncio.shield(conexion.cerrar())
        except Exception as error:  # noqa: BLE001
            self._registro.warning(EVENTO_CIERRE_FALLIDO, error=type(error).__name__)

    def _procesar(self, notificacion: NotificacionDeCanal) -> None:
        if notificacion.canal != CANAL_CAMBIOS_INCIDENCIAS:
            return
        try:
            cambio = leer_cambio(notificacion.payload)
        except ValueError as error:
            self._registro.warning(EVENTO_NOTIFICACION_DESCARTADA, error=type(error).__name__)
            return
        if cambio is None:
            self._publicar.publicar_cambio()
            return
        tarea = asyncio.create_task(self._publicar.execute([cambio]))
        self._publicaciones.add(tarea)
        tarea.add_done_callback(self._publicaciones.discard)
