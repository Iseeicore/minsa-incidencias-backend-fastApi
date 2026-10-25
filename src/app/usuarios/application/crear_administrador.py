from typing import TYPE_CHECKING

from app.constants.actores import ACTOR_SISTEMA_CREAR_ADMIN
from app.constants.textos.usuarios import MENSAJE_AREA_DEL_ADMINISTRADOR_INEXISTENTE, MENSAJE_CORREO_YA_EXISTE
from app.enums.rol_codigo import RolCodigo
from app.errors.conflicto import Conflicto
from app.errors.correo_repetido import CorreoRepetido
from app.shared.correo import normalizar_correo
from app.usuarios.application.areas import area_opcional_o_error
from app.usuarios.domain.pedidos import NuevoUsuarioFila

if TYPE_CHECKING:
    from app.shared.ports import PasswordHasher
    from app.usuarios.application.ports import UsuarioUnitOfWork
    from app.usuarios.domain.pedidos import DatosDeAdministrador


class CrearAdministrador:
    def __init__(self, unidad: UsuarioUnitOfWork, hasher: PasswordHasher) -> None:
        self._unidad = unidad
        self._hasher = hasher

    async def execute(self, datos: DatosDeAdministrador) -> None:
        huella = await self._hasher.hash(datos.password)
        try:
            async with self._unidad.begin(ACTOR_SISTEMA_CREAR_ADMIN) as tx:
                area_id = await area_opcional_o_error(tx, datos.area, MENSAJE_AREA_DEL_ADMINISTRADOR_INEXISTENTE)
                fila = NuevoUsuarioFila(datos.nombre_completo, normalizar_correo(datos.correo), huella, area_id)
                usuario_id = await tx.crear(fila)
                await tx.asignar_rol(usuario_id, RolCodigo.ADMINISTRADOR)
        except CorreoRepetido as error:
            raise Conflicto(MENSAJE_CORREO_YA_EXISTE) from error
