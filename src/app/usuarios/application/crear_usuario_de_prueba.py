from typing import TYPE_CHECKING

from app.constants.actores import ACTOR_SISTEMA_USUARIO_PRUEBA
from app.constants.textos.usuarios import MENSAJE_AREA_DE_PRUEBA_INEXISTENTE, MENSAJE_ROL_DE_PRUEBA_INEXISTENTE
from app.enums.resultado_usuario_de_prueba import ResultadoUsuarioDePrueba
from app.errors.correo_repetido import CorreoRepetido
from app.errors.no_procesable import NoProcesable
from app.shared.correo import normalizar_correo
from app.usuarios.application.areas import area_opcional_o_error
from app.usuarios.domain.pedidos import NuevoUsuarioFila

if TYPE_CHECKING:
    from app.shared.ports import PasswordHasher
    from app.usuarios.application.ports import UsuarioUnitOfWork
    from app.usuarios.domain.pedidos import DatosDeUsuarioDePrueba


class CrearUsuarioDePrueba:
    def __init__(self, unidad: UsuarioUnitOfWork, hasher: PasswordHasher) -> None:
        self._unidad = unidad
        self._hasher = hasher

    async def execute(self, datos: DatosDeUsuarioDePrueba) -> ResultadoUsuarioDePrueba:
        correo = normalizar_correo(datos.correo)
        async with self._unidad.begin(ACTOR_SISTEMA_USUARIO_PRUEBA) as tx:
            if not await tx.rol_activo(datos.rol):
                raise NoProcesable(MENSAJE_ROL_DE_PRUEBA_INEXISTENTE.format(rol=datos.rol.value))
            area_id = await area_opcional_o_error(tx, datos.area, MENSAJE_AREA_DE_PRUEBA_INEXISTENTE)
            if await tx.correo_existe(correo):
                return ResultadoUsuarioDePrueba.EXISTENTE
            huella = await self._hasher.hash(datos.password)
            try:
                usuario_id = await tx.crear(NuevoUsuarioFila(datos.nombre_completo, correo, huella, area_id))
            except CorreoRepetido:
                return ResultadoUsuarioDePrueba.EXISTENTE
            await tx.asignar_rol(usuario_id, datos.rol)
        return ResultadoUsuarioDePrueba.CREADO
