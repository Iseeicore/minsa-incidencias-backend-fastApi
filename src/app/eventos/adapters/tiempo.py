import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.eventos.domain.ports import Cancelar


class _Repeticion:
    def __init__(self, accion: Callable[[], None], segundos: float) -> None:
        self._bucle = asyncio.get_running_loop()
        self._accion = accion
        self._segundos = segundos
        self._turno = self._bucle.call_later(segundos, self._latir)

    def _latir(self) -> None:
        self._turno = self._bucle.call_later(self._segundos, self._latir)
        self._accion()

    def cancelar(self) -> None:
        self._turno.cancel()


class TiempoAsyncio:
    def ahora(self) -> datetime:
        return datetime.now(UTC)

    def programar(self, accion: Callable[[], None], segundos: float) -> Cancelar:
        return asyncio.get_running_loop().call_later(segundos, accion).cancel

    def repetir(self, accion: Callable[[], None], segundos: float) -> Cancelar:
        return _Repeticion(accion, segundos).cancelar
