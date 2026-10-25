from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.shared.sesion import SesionActual


class SinSesiones:
    async def resolve(self, session_id: str) -> SesionActual | None:  # noqa: ARG002
        return None
