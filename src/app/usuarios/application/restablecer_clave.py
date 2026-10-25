from typing import TYPE_CHECKING

from app.shared.actor import actor_usuario_interno
from app.shared.clave_inicial import generar_clave_inicial
from app.usuarios.domain.gestion import exigir_gestion, restriccion_de, usuario_no_encontrado
from app.usuarios.domain.pedidos import UsuarioConClave

if TYPE_CHECKING:
    from app.shared.ports import PasswordHasher
    from app.shared.sesion import SesionActual
    from app.usuarios.application.ports import UsuarioUnitOfWork


class RestablecerClave:
    def __init__(self, unidad: UsuarioUnitOfWork, hasher: PasswordHasher) -> None:
        self._unidad = unidad
        self._hasher = hasher

    async def execute(self, sesion: SesionActual, usuario_id: str) -> UsuarioConClave:
        gestion = exigir_gestion(sesion.roles)
        clave_inicial = generar_clave_inicial()
        huella = await self._hasher.hash(clave_inicial)
        async with self._unidad.begin(actor_usuario_interno(sesion.correo)) as tx:
            actual = await tx.buscar_por_id(usuario_id, restriccion_de(sesion, gestion), bloquear=True)
            if actual is None:
                raise usuario_no_encontrado()
            await tx.cambiar_clave(usuario_id, huella)
            await tx.cerrar_sesiones(usuario_id)
        return UsuarioConClave(actual, clave_inicial)
