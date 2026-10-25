import asyncio
from typing import TYPE_CHECKING

from app.constants.eventos import EVENTOS_CATEGORIAS_CACHE_SEGUNDOS
from app.constants.textos.eventos import EVENTO_CATEGORIAS_NO_LEIDAS

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from app.eventos.application.ports import CategoriasReader
    from app.eventos.domain.cambio_de_incidencia import CambioDeIncidencia, CategoriasPorRol
    from app.eventos.domain.centro_de_eventos import CentroDeEventos
    from app.eventos.domain.ports import TiempoDeEventos
    from app.shared.ports import RegistroDeProcesos


class PublicarCambios:
    def __init__(
        self,
        centro: CentroDeEventos,
        categorias: CategoriasReader,
        tiempo: TiempoDeEventos,
        registro: RegistroDeProcesos,
    ) -> None:
        self._centro = centro
        self._categorias = categorias
        self._tiempo = tiempo
        self._registro = registro
        self._cache: tuple[datetime, asyncio.Task[CategoriasPorRol]] | None = None

    async def execute(self, cambios: Sequence[CambioDeIncidencia]) -> None:
        if self._centro.conectados == 0 or not cambios:
            return
        try:
            por_rol = await asyncio.shield(self._categorias_por_rol())
        except Exception as error:  # noqa: BLE001
            self._registro.warning(EVENTO_CATEGORIAS_NO_LEIDAS, error=type(error).__name__)
            return
        self._centro.publicar(cambios, por_rol)

    def publicar_cambio(self) -> None:
        self._centro.publicar_cambio()

    def _categorias_por_rol(self) -> asyncio.Task[CategoriasPorRol]:
        ahora = self._tiempo.ahora()
        if self._cache is None or (ahora - self._cache[0]).total_seconds() >= EVENTOS_CATEGORIAS_CACHE_SEGUNDOS:
            tarea = asyncio.ensure_future(self._categorias.categorias_por_rol())
            tarea.add_done_callback(self._olvidar_si_fallo)
            self._cache = (ahora, tarea)
        return self._cache[1]

    def _olvidar_si_fallo(self, tarea: asyncio.Task[CategoriasPorRol]) -> None:
        fallo = tarea.cancelled() or tarea.exception() is not None
        if fallo and self._cache is not None and self._cache[1] is tarea:
            self._cache = None
