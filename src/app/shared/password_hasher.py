import asyncio

from argon2 import PasswordHasher as Argon2
from argon2.exceptions import InvalidHashError, VerificationError

from app.shared.argon2_hash import canonical_argon2_hash


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = Argon2()

    async def hash(self, plain: str) -> str:
        return await asyncio.to_thread(self._hasher.hash, plain)

    async def verify(self, hashed: str, plain: str) -> bool:
        return await asyncio.to_thread(self._verify, hashed, plain)

    def _verify(self, hashed: str, plain: str) -> bool:
        try:
            return self._hasher.verify(canonical_argon2_hash(hashed), plain)
        except VerificationError, InvalidHashError:
            return False
