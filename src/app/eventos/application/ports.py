from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.eventos.domain.cambio_de_incidencia import CategoriasPorRol


@dataclass(frozen=True, slots=True)
class NotificacionDeCanal:
    canal: str
    payload: str | None = None


class CategoriasReader(Protocol):
    async def categorias_por_rol(self) -> CategoriasPorRol: ...


class ConexionDeNotificaciones(Protocol):
    def notificaciones(self) -> AsyncIterator[NotificacionDeCanal]: ...

    async def cerrar(self) -> None: ...


class AbridorDeConexion(Protocol):
    async def abrir(self) -> ConexionDeNotificaciones: ...


class InstaladorDeNotificaciones(Protocol):
    async def instalar(self) -> None: ...
