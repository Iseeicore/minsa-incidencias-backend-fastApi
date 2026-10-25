import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

type Ciclo = Callable[[], Awaitable[None]]


async def repetir_hasta_parar(
    ciclo: Ciclo, parar: asyncio.Event, intervalo_segundos: float, *, una_vez: bool = False
) -> None:
    while not parar.is_set():
        await ciclo()
        if una_vez:
            return
        with suppress(TimeoutError):
            await asyncio.wait_for(parar.wait(), intervalo_segundos)


class CicloPeriodico:
    def __init__(self, ciclo: Ciclo, intervalo_segundos: float) -> None:
        self._ciclo = ciclo
        self._intervalo_segundos = intervalo_segundos
        self._parar = asyncio.Event()
        self._tarea: asyncio.Task[None] | None = None

    def iniciar(self) -> None:
        if self._tarea is None:
            self._tarea = asyncio.create_task(repetir_hasta_parar(self._ciclo, self._parar, self._intervalo_segundos))

    async def detener(self) -> None:
        self._parar.set()
        if self._tarea is not None:
            await self._tarea
            self._tarea = None


class ProcesosDeFondo:
    def __init__(self, ciclos: Iterable[CicloPeriodico]) -> None:
        self._ciclos = tuple(ciclos)

    def iniciar(self) -> None:
        for ciclo in self._ciclos:
            ciclo.iniciar()

    async def detener(self) -> None:
        await asyncio.gather(*(ciclo.detener() for ciclo in self._ciclos))
