from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants.cursor import PAGINA_EXTRA

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


@dataclass(frozen=True, slots=True)
class Pagina[T]:
    items: list[T]
    siguiente: str | None
    hay_mas: bool


def pagina_de[T](filas: Sequence[T], limite: int, cursor_de: Callable[[T], str]) -> Pagina[T]:
    hay_mas = len(filas) > limite
    pagina = list(filas[:limite]) if hay_mas else list(filas)
    siguiente = cursor_de(pagina[-1]) if hay_mas and pagina else None
    return Pagina(pagina, siguiente, hay_mas)


def limite_con_extra(limite: int) -> int:
    return limite + PAGINA_EXTRA
