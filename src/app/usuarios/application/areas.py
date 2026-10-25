from typing import TYPE_CHECKING

from app.constants.textos.usuarios import (
    MENSAJE_ADMINISTRADOR_SIN_AREA,
    MENSAJE_AREA_INVALIDA,
    MENSAJE_AREA_OBLIGATORIA,
    MENSAJE_SIN_AREA_PROPIA,
)
from app.enums.alcance_de_usuarios import AlcanceDeUsuarios
from app.enums.rol_codigo import RolCodigo
from app.errors.no_procesable import NoProcesable
from app.errors.sin_permiso import SinPermiso

if TYPE_CHECKING:
    from app.shared.permisos import GestionDeUsuarios
    from app.shared.sesion import SesionActual
    from app.usuarios.application.ports import UsuarioTransaction
    from app.usuarios.domain.pedidos import DatosNuevoUsuario


async def area_activa_o_error(tx: UsuarioTransaction, codigo: str) -> int:
    area_id = await tx.area_activa(codigo)
    if area_id is None:
        raise NoProcesable(MENSAJE_AREA_INVALIDA)
    return area_id


async def area_para_crear(
    tx: UsuarioTransaction, sesion: SesionActual, gestion: GestionDeUsuarios, datos: DatosNuevoUsuario
) -> int | None:
    if gestion.alcance == AlcanceDeUsuarios.SU_AREA:
        if sesion.area is None:
            raise SinPermiso(MENSAJE_SIN_AREA_PROPIA)
        return sesion.area.id
    if datos.rol == RolCodigo.ADMINISTRADOR:
        if datos.area:
            raise NoProcesable(MENSAJE_ADMINISTRADOR_SIN_AREA)
        return None
    if not datos.area:
        raise NoProcesable(MENSAJE_AREA_OBLIGATORIA)
    return await area_activa_o_error(tx, datos.area)
