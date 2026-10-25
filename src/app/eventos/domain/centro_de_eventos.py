from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from app.constants.eventos import (
    EVENTOS_AGRUPADO_SEGUNDOS,
    EVENTOS_CARACTERES_VISIBLES,
    EVENTOS_LATIDO_SEGUNDOS,
    EVENTOS_MAX_POR_USUARIO,
    EVENTOS_MAX_TOTAL,
)
from app.constants.incidencias import DNI_ENMASCARADO
from app.constants.textos.eventos import EVENTO_FLUJO_ABIERTO, EVENTO_FLUJO_CERRADO
from app.enums.evento_nombre import EventoNombre
from app.enums.motivo_de_cierre import MotivoDeCierre
from app.errors.demasiadas_conexiones import DemasiadasConexiones
from app.errors.sesion_invalida import SesionInvalida
from app.eventos.domain.cambio_de_incidencia import alcance_de_eventos, recibe_cambio

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from app.eventos.domain.cambio_de_incidencia import CambioDeIncidencia, CategoriasPorRol
    from app.eventos.domain.ports import Cancelar, DarDeBaja, Suscriptor, TiempoDeEventos
    from app.shared.ports import ControlDeSesion, RegistroDeProcesos
    from app.shared.sesion import SesionEnVivo


@dataclass(slots=True, eq=False)
class _Cliente:
    sesion: SesionEnVivo
    suscriptor: Suscriptor
    pendiente: Cancelar | None = None
    vencimiento: Cancelar | None = None


@dataclass(slots=True, eq=False)
class _Verificacion:
    sesion_id: str
    usuario_id: str | None
    invalidada: bool
    usuarios_invalidados: set[str] = field(default_factory=set)


def enmascarar_identificador(identificador: str) -> str:
    visible = identificador[-EVENTOS_CARACTERES_VISIBLES:] if len(identificador) > EVENTOS_CARACTERES_VISIBLES else ""
    return f"{DNI_ENMASCARADO}{visible}"


class _ControlDeVerificacion:
    def __init__(self, verificacion: _Verificacion, liberar: Callable[[_Verificacion], None]) -> None:
        self._verificacion = verificacion
        self._liberar = liberar

    def identificar(self, usuario_id: str) -> bool:
        verificacion = self._verificacion
        cambia_de_usuario = verificacion.usuario_id is not None and verificacion.usuario_id != usuario_id
        verificacion.invalidada = (
            verificacion.invalidada or usuario_id in verificacion.usuarios_invalidados or cambia_de_usuario
        )
        verificacion.usuario_id = usuario_id
        verificacion.usuarios_invalidados.clear()
        return not verificacion.invalidada

    def vigente(self) -> bool:
        return not self._verificacion.invalidada

    def liberar(self) -> None:
        self._verificacion.invalidada = True
        self._liberar(self._verificacion)


class CentroDeEventos:
    def __init__(self, tiempo: TiempoDeEventos, registro: RegistroDeProcesos) -> None:
        self._tiempo = tiempo
        self._registro = registro
        self._clientes: dict[_Cliente, None] = {}
        self._verificaciones: dict[_Verificacion, None] = {}
        self._cerrado = False
        self._latido: Cancelar | None = None

    @property
    def conectados(self) -> int:
        return len(self._clientes)

    def iniciar_verificacion(self, sesion_id: str) -> ControlDeSesion:
        verificacion = _Verificacion(sesion_id, None, invalidada=self._cerrado)
        self._verificaciones[verificacion] = None
        return _ControlDeVerificacion(verificacion, lambda liberada: self._verificaciones.pop(liberada, None))

    def invalidar_sesion(self, sesion_id: str) -> None:
        for verificacion in self._verificaciones:
            if verificacion.sesion_id == sesion_id:
                verificacion.invalidada = True
        for cliente in list(self._clientes):
            if cliente.sesion.sesion_id == sesion_id:
                self._terminar_sesion(cliente)

    def invalidar_usuario(self, usuario_id: str) -> None:
        for verificacion in self._verificaciones:
            if verificacion.usuario_id is None:
                verificacion.usuarios_invalidados.add(usuario_id)
            elif verificacion.usuario_id == usuario_id:
                verificacion.invalidada = True
        for cliente in list(self._clientes):
            if cliente.sesion.usuario_id == usuario_id:
                self._terminar_sesion(cliente)

    def actualizar_sesion(self, sesion: SesionEnVivo) -> None:
        if not sesion.control.vigente():
            return
        for cliente in list(self._clientes):
            if cliente.sesion.sesion_id != sesion.sesion_id:
                continue
            vigencia = replace(
                cliente.sesion.vigencia,
                vence_en=min(cliente.sesion.vigencia.vence_en, sesion.vigencia.vence_en),
                inactiva_en=max(cliente.sesion.vigencia.inactiva_en, sesion.vigencia.inactiva_en),
            )
            cliente.sesion = replace(
                cliente.sesion, roles=tuple(sesion.roles), area_id=sesion.area_id, vigencia=vigencia
            )
            self._programar_vencimiento(cliente)

    def suscribir(self, sesion: SesionEnVivo, suscriptor: Suscriptor) -> DarDeBaja:
        if self._cerrado or not sesion.control.vigente() or self._vencida(sesion):
            raise SesionInvalida
        del_usuario = sum(1 for cliente in self._clientes if cliente.sesion.usuario_id == sesion.usuario_id)
        if del_usuario >= EVENTOS_MAX_POR_USUARIO or len(self._clientes) >= EVENTOS_MAX_TOTAL:
            raise DemasiadasConexiones
        cliente = _Cliente(sesion, suscriptor)
        self._clientes[cliente] = None
        self._programar_vencimiento(cliente)
        if len(self._clientes) == 1:
            self._latido = self._tiempo.repetir(self._latir, EVENTOS_LATIDO_SEGUNDOS)
        self._registro.info(
            EVENTO_FLUJO_ABIERTO, usuario=enmascarar_identificador(sesion.usuario_id), conectados=len(self._clientes)
        )
        return self._dar_de_baja(cliente)

    def publicar(self, cambios: Sequence[CambioDeIncidencia], categorias_por_rol: CategoriasPorRol) -> None:
        if not self._clientes or not cambios:
            return
        for cliente in list(self._clientes):
            alcance = alcance_de_eventos(cliente.sesion.roles, cliente.sesion.area_id, categorias_por_rol)
            if any(recibe_cambio(alcance, cambio) for cambio in cambios):
                self._avisar(cliente)

    def publicar_cambio(self) -> None:
        for cliente in list(self._clientes):
            self._avisar(cliente)

    def cerrar_todo(self) -> None:
        self._cerrado = True
        for verificacion in self._verificaciones:
            verificacion.invalidada = True
        self._verificaciones.clear()
        for cliente in list(self._clientes):
            if self._quitar(cliente, MotivoDeCierre.APAGADO):
                cliente.suscriptor.cerrar(MotivoDeCierre.APAGADO)

    def _dar_de_baja(self, cliente: _Cliente) -> DarDeBaja:
        def dar_de_baja() -> None:
            self._quitar(cliente, MotivoDeCierre.CLIENTE)

        return dar_de_baja

    def _latir(self) -> None:
        for cliente in list(self._clientes):
            if self._comprobar(cliente):
                cliente.suscriptor.latido()

    def _avisar(self, cliente: _Cliente) -> None:
        if not self._comprobar(cliente) or cliente.pendiente is not None:
            return

        def enviar() -> None:
            cliente.pendiente = None
            if self._comprobar(cliente):
                cliente.suscriptor.enviar(EventoNombre.CAMBIO)

        cliente.pendiente = self._tiempo.programar(enviar, EVENTOS_AGRUPADO_SEGUNDOS)

    def _vencida(self, sesion: SesionEnVivo) -> bool:
        return self._tiempo.ahora() >= min(sesion.vigencia.vence_en, sesion.vigencia.inactiva_en)

    def _comprobar(self, cliente: _Cliente) -> bool:
        if cliente not in self._clientes:
            return False
        if cliente.sesion.control.vigente() and not self._vencida(cliente.sesion):
            return True
        self._terminar_sesion(cliente)
        return False

    def _programar_vencimiento(self, cliente: _Cliente) -> None:
        if cliente.vencimiento is not None:
            cliente.vencimiento()
            cliente.vencimiento = None
        vence_en = min(cliente.sesion.vigencia.vence_en, cliente.sesion.vigencia.inactiva_en)
        espera = max(0.0, (vence_en - self._tiempo.ahora()).total_seconds())

        def vencer() -> None:
            cliente.vencimiento = None
            if self._comprobar(cliente):
                self._programar_vencimiento(cliente)

        cliente.vencimiento = self._tiempo.programar(vencer, espera)

    def _terminar_sesion(self, cliente: _Cliente) -> None:
        if not self._quitar(cliente, MotivoDeCierre.SESION_INVALIDA):
            return
        try:
            cliente.suscriptor.enviar(EventoNombre.SESION)
        finally:
            cliente.suscriptor.cerrar(MotivoDeCierre.SESION_INVALIDA)

    def _quitar(self, cliente: _Cliente, motivo: MotivoDeCierre) -> bool:
        if cliente not in self._clientes:
            return False
        del self._clientes[cliente]
        if cliente.pendiente is not None:
            cliente.pendiente()
            cliente.pendiente = None
        if cliente.vencimiento is not None:
            cliente.vencimiento()
            cliente.vencimiento = None
        cliente.sesion.control.liberar()
        if not self._clientes and self._latido is not None:
            self._latido()
            self._latido = None
        self._registro.info(
            EVENTO_FLUJO_CERRADO,
            usuario=enmascarar_identificador(cliente.sesion.usuario_id),
            motivo=motivo.value,
            conectados=len(self._clientes),
        )
        return True
