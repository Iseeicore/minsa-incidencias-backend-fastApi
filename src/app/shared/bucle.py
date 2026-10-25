import asyncio
import selectors
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Coroutine


def ejecutar_corutina[T](corutina: Coroutine[object, object, T]) -> T:
    fabrica = (lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())) if sys.platform == "win32" else None
    return asyncio.run(corutina, loop_factory=fabrica)
