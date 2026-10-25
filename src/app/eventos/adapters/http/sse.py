import asyncio
from typing import TYPE_CHECKING

from app.constants.eventos import EVENTOS_COMENTARIO_DE_LATIDO, EVENTOS_DATOS_VACIOS, EVENTOS_REINTENTO_MS

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from app.enums.evento_nombre import EventoNombre
    from app.enums.motivo_de_cierre import MotivoDeCierre
    from app.eventos.domain.ports import DarDeBaja

ANUNCIO_DE_REINTENTO = f"retry: {EVENTOS_REINTENTO_MS}\n\n"
LATIDO = f": {EVENTOS_COMENTARIO_DE_LATIDO}\n\n"


class SuscriptorSse:
    def __init__(self) -> None:
        self._cola: asyncio.Queue[str | None] = asyncio.Queue()
        self._cerrado = False

    def enviar(self, evento: EventoNombre) -> None:
        self._poner(f"event: {evento.value}\ndata: {EVENTOS_DATOS_VACIOS}\n\n")

    def latido(self) -> None:
        self._poner(LATIDO)

    def cerrar(self, motivo: MotivoDeCierre) -> None:
        del motivo
        self._poner(None)
        self._cerrado = True

    def _poner(self, trozo: str | None) -> None:
        if not self._cerrado:
            self._cola.put_nowait(trozo)

    async def flujo(self, dar_de_baja: DarDeBaja) -> AsyncGenerator[str]:
        try:
            yield ANUNCIO_DE_REINTENTO
            while (trozo := await self._cola.get()) is not None:
                yield trozo
        finally:
            dar_de_baja()
