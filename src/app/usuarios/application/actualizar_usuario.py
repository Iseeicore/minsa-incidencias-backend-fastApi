from typing import TYPE_CHECKING

from app.constants.textos.usuarios import (
    MENSAJE_ADMINISTRADOR_SIN_AREA,
    MENSAJE_AREA_NO_PERMITIDA,
    MENSAJE_AREA_OBLIGATORIA,
)
from app.enums.alcance_de_usuarios import AlcanceDeUsuarios
from app.enums.rol_codigo import RolCodigo
from app.errors.autoedicion_no_permitida import AutoedicionNoPermitida
from app.errors.no_procesable import NoProcesable
from app.errors.sin_permiso import SinPermiso
from app.shared.actor import actor_usuario_interno
from app.usuarios.application.areas import area_activa_o_error
from app.usuarios.domain.gestion import exigir_gestion, exigir_rol_asignable, restriccion_de, usuario_no_encontrado

if TYPE_CHECKING:
    from app.shared.permisos import GestionDeUsuarios
    from app.shared.ports import InvalidadorDeUsuarios
    from app.shared.sesion import SesionActual
    from app.usuarios.application.ports import UsuarioTransaction, UsuarioUnitOfWork
    from app.usuarios.domain.pedidos import CambiosDeUsuario
    from app.usuarios.domain.usuario_gestionado import UsuarioGestionado


def _cambia_rol(actual: UsuarioGestionado, cambios: CambiosDeUsuario) -> bool:
    return cambios.rol is not None and cambios.rol != actual.rol


def _afecta_la_sesion(actual: UsuarioGestionado, cambios: CambiosDeUsuario, area_final: int | None) -> bool:
    cambia_vigencia = cambios.activo is not None and cambios.activo != actual.activo
    return _cambia_rol(actual, cambios) or area_final != actual.area_id or cambia_vigencia


async def _area_final(
    tx: UsuarioTransaction, gestion: GestionDeUsuarios, actual: UsuarioGestionado, cambios: CambiosDeUsuario
) -> int | None:
    rol_final = cambios.rol if cambios.rol is not None else actual.rol
    area_final = actual.area_id
    if cambios.area is not None:
        if gestion.alcance != AlcanceDeUsuarios.TODAS:
            if cambios.area != actual.area_codigo:
                raise SinPermiso(MENSAJE_AREA_NO_PERMITIDA)
        elif rol_final == RolCodigo.ADMINISTRADOR:
            raise NoProcesable(MENSAJE_ADMINISTRADOR_SIN_AREA)
        else:
            area_final = await area_activa_o_error(tx, cambios.area)
    if rol_final == RolCodigo.ADMINISTRADOR:
        return None
    if _cambia_rol(actual, cambios) and area_final is None:
        raise NoProcesable(MENSAJE_AREA_OBLIGATORIA)
    return area_final


class ActualizarUsuario:
    def __init__(self, unidad: UsuarioUnitOfWork, seguimiento: InvalidadorDeUsuarios | None = None) -> None:
        self._unidad = unidad
        self._seguimiento = seguimiento

    async def execute(self, sesion: SesionActual, usuario_id: str, cambios: CambiosDeUsuario) -> UsuarioGestionado:
        gestion = exigir_gestion(sesion.roles)
        actor = actor_usuario_interno(sesion.correo)
        async with self._unidad.begin(actor) as tx:
            actual = await tx.buscar_por_id(usuario_id, restriccion_de(sesion, gestion), bloquear=True)
            if actual is None:
                raise usuario_no_encontrado()
            self._validar(sesion, gestion, actual, cambios)
            area_final = await _area_final(tx, gestion, actual, cambios)
            await self._escribir(tx, actual, cambios, area_final, actor)
            recargado = await tx.buscar_por_id(usuario_id, None)
            if recargado is None:
                raise usuario_no_encontrado()
        if self._seguimiento is not None and _afecta_la_sesion(actual, cambios, area_final):
            self._seguimiento.invalidar_usuario(usuario_id)
        return recargado

    def _validar(
        self, sesion: SesionActual, gestion: GestionDeUsuarios, actual: UsuarioGestionado, cambios: CambiosDeUsuario
    ) -> None:
        if cambios.rol is not None:
            exigir_rol_asignable(gestion, cambios.rol)
        es_uno_mismo = actual.id == sesion.usuario_id
        if es_uno_mismo and (_cambia_rol(actual, cambios) or cambios.activo is False):
            raise AutoedicionNoPermitida

    async def _escribir(
        self,
        tx: UsuarioTransaction,
        actual: UsuarioGestionado,
        cambios: CambiosDeUsuario,
        area_final: int | None,
        actor: str,
    ) -> None:
        cambia_rol = _cambia_rol(actual, cambios)
        if cambia_rol:
            await tx.quitar_roles(actual.id)
        if area_final != actual.area_id:
            await tx.cambiar_area(actual.id, area_final)
        if cambia_rol and cambios.rol is not None:
            await tx.asignar_rol(actual.id, cambios.rol)
            await tx.cerrar_sesiones(actual.id)
        if cambios.nombre_completo is not None and cambios.nombre_completo != actual.nombre_completo:
            await tx.cambiar_nombre(actual.id, cambios.nombre_completo)
        if cambios.activo is not None and cambios.activo != actual.activo:
            await tx.cambiar_vigencia(actual.id, activo=cambios.activo, actor=actor)
