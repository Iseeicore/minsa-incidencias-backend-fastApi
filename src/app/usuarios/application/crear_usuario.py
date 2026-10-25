from typing import TYPE_CHECKING

from app.shared.actor import actor_usuario_interno
from app.shared.clave_inicial import generar_clave_inicial
from app.usuarios.application.areas import area_para_crear
from app.usuarios.domain.gestion import exigir_gestion, exigir_rol_asignable, usuario_no_encontrado
from app.usuarios.domain.pedidos import NuevoUsuarioFila, UsuarioConClave

if TYPE_CHECKING:
    from app.shared.ports import PasswordHasher
    from app.shared.sesion import SesionActual
    from app.usuarios.application.ports import UsuarioUnitOfWork
    from app.usuarios.domain.pedidos import DatosNuevoUsuario


class CrearUsuario:
    def __init__(self, unidad: UsuarioUnitOfWork, hasher: PasswordHasher) -> None:
        self._unidad = unidad
        self._hasher = hasher

    async def execute(self, sesion: SesionActual, datos: DatosNuevoUsuario) -> UsuarioConClave:
        gestion = exigir_gestion(sesion.roles)
        exigir_rol_asignable(gestion, datos.rol)
        clave_inicial = generar_clave_inicial()
        huella = await self._hasher.hash(clave_inicial)
        async with self._unidad.begin(actor_usuario_interno(sesion.correo)) as tx:
            area_id = await area_para_crear(tx, sesion, gestion, datos)
            fila = NuevoUsuarioFila(datos.nombre_completo, datos.correo, huella, area_id)
            usuario_id = await tx.crear(fila)
            await tx.asignar_rol(usuario_id, datos.rol)
            usuario = await tx.buscar_por_id(usuario_id, None)
            if usuario is None:
                raise usuario_no_encontrado()
        return UsuarioConClave(usuario, clave_inicial)
