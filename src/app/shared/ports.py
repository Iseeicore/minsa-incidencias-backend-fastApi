from typing import Protocol


class DatabaseProbe(Protocol):
    async def ping(self) -> bool: ...
