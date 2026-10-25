from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.shared.sesion import SesionActual


class DatabaseProbe(Protocol):
    async def ping(self) -> bool: ...


class PasswordHasher(Protocol):
    async def hash(self, plain: str) -> str: ...

    async def verify(self, hashed: str, plain: str) -> bool: ...


class SessionResolver(Protocol):
    async def resolve(self, session_id: str) -> SesionActual | None: ...
