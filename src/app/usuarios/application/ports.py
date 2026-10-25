from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from app.enums.rol_codigo import RolCodigo
    from app.shared.cursor import PosicionPorNombre
    from app.usuarios.domain.pedidos import FiltrosDeUsuarios, NuevoUsuarioFila, RestriccionDeArea
    from app.usuarios.domain.usuario_gestionado import UsuarioGestionado


class UsuarioReader(Protocol):
    async def listar(
        self, filtros: FiltrosDeUsuarios, limite: int, despues_de: PosicionPorNombre[str] | None
    ) -> list[UsuarioGestionado]: ...


class UsuarioTransaction(Protocol):
    async def buscar_por_id(
        self, usuario_id: str, restriccion: RestriccionDeArea | None, *, bloquear: bool = False
    ) -> UsuarioGestionado | None: ...

    async def area_activa(self, codigo: str) -> int | None: ...

    async def rol_activo(self, rol: RolCodigo) -> bool: ...

    async def correo_existe(self, correo: str) -> bool: ...

    async def crear(self, datos: NuevoUsuarioFila) -> str: ...

    async def asignar_rol(self, usuario_id: str, rol: RolCodigo) -> None: ...

    async def quitar_roles(self, usuario_id: str) -> None: ...

    async def cambiar_area(self, usuario_id: str, area_id: int | None) -> None: ...

    async def cambiar_nombre(self, usuario_id: str, nombre_completo: str) -> None: ...

    async def cambiar_vigencia(self, usuario_id: str, *, activo: bool, actor: str) -> None: ...

    async def cambiar_clave(self, usuario_id: str, huella: str) -> None: ...

    async def cerrar_sesiones(self, usuario_id: str) -> None: ...


class UsuarioUnitOfWork(Protocol):
    def begin(self, actor: str) -> AbstractAsyncContextManager[UsuarioTransaction]: ...
