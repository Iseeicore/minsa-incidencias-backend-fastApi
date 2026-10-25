from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from app.enums.evento_nombre import EventoNombre
    from app.enums.motivo_de_cierre import MotivoDeCierre

type DarDeBaja = Callable[[], None]
type Cancelar = Callable[[], None]


class Suscriptor(Protocol):
    def enviar(self, evento: EventoNombre) -> None: ...

    def latido(self) -> None: ...

    def cerrar(self, motivo: MotivoDeCierre) -> None: ...


class TiempoDeEventos(Protocol):
    def ahora(self) -> datetime: ...

    def programar(self, accion: Callable[[], None], segundos: float) -> Cancelar: ...

    def repetir(self, accion: Callable[[], None], segundos: float) -> Cancelar: ...
