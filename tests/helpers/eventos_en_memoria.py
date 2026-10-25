from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.enums.rol_codigo import RolCodigo
from app.shared.sesion import SesionEnVivo, VigenciaDeSesion

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.enums.evento_nombre import EventoNombre
    from app.enums.motivo_de_cierre import MotivoDeCierre
    from app.eventos.domain.cambio_de_incidencia import CategoriasPorRol

INICIO = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
CORRUPCION = 1
QUEJA = 2
CATEGORIAS: CategoriasPorRol = {
    RolCodigo.ADMINISTRADOR: {CORRUPCION, QUEJA},
    RolCodigo.GESTOR: {QUEJA},
    RolCodigo.ESTABLECIMIENTO: {QUEJA},
    RolCodigo.OTRANS: {CORRUPCION},
}


@dataclass(slots=True)
class _Tarea:
    momento: datetime
    orden: int
    accion: Callable[[], None]
    cada: float | None = None
    cancelada: bool = False


class TiempoManual:
    def __init__(self, inicio: datetime = INICIO) -> None:
        self._ahora = inicio
        self._tareas: list[_Tarea] = []
        self._orden = 0

    def ahora(self) -> datetime:
        return self._ahora

    @property
    def pendientes(self) -> int:
        return sum(1 for tarea in self._tareas if not tarea.cancelada)

    def programar(self, accion: Callable[[], None], segundos: float) -> Callable[[], None]:
        return self._agregar(accion, segundos, None)

    def repetir(self, accion: Callable[[], None], segundos: float) -> Callable[[], None]:
        return self._agregar(accion, segundos, segundos)

    def _agregar(self, accion: Callable[[], None], segundos: float, cada: float | None) -> Callable[[], None]:
        self._orden += 1
        tarea = _Tarea(self._ahora + timedelta(seconds=segundos), self._orden, accion, cada)
        self._tareas.append(tarea)

        def cancelar() -> None:
            tarea.cancelada = True

        return cancelar

    def disparar_sin_avanzar(self) -> None:
        for tarea in [t for t in self._tareas if not t.cancelada and t.cada is None]:
            tarea.cancelada = True
            tarea.accion()

    def avanzar(self, segundos: float) -> None:
        limite = self._ahora + timedelta(seconds=segundos)
        while True:
            vivas = [t for t in self._tareas if not t.cancelada and t.momento <= limite]
            if not vivas:
                break
            tarea = min(vivas, key=lambda t: (t.momento, t.orden))
            self._ahora = tarea.momento
            if tarea.cada is None:
                tarea.cancelada = True
            else:
                tarea.momento += timedelta(seconds=tarea.cada)
            tarea.accion()
        self._ahora = limite
        self._tareas = [t for t in self._tareas if not t.cancelada]


class ControlDePrueba:
    def __init__(self) -> None:
        self.activo = True
        self.identificados: list[str] = []

    def identificar(self, usuario_id: str) -> bool:
        self.identificados.append(usuario_id)
        return self.activo

    def vigente(self) -> bool:
        return self.activo

    def liberar(self) -> None:
        self.activo = False


@dataclass(slots=True)
class SuscriptorFalso:
    enviados: list[EventoNombre] = field(default_factory=list)
    latidos: int = 0
    cierres: list[MotivoDeCierre] = field(default_factory=list)

    def enviar(self, evento: EventoNombre) -> None:
        self.enviados.append(evento)

    def latido(self) -> None:
        self.latidos += 1

    def cerrar(self, motivo: MotivoDeCierre) -> None:
        self.cierres.append(motivo)


def una_vigencia(
    vence_en: datetime | None = None, inactiva_en: datetime | None = None, inicio: datetime = INICIO
) -> VigenciaDeSesion:
    return VigenciaDeSesion(
        vence_en=vence_en or inicio + timedelta(hours=8), inactiva_en=inactiva_en or inicio + timedelta(minutes=30)
    )


def una_sesion_en_vivo(  # noqa: PLR0913
    rol: str = RolCodigo.GESTOR,
    area_id: int | None = 21,
    *,
    usuario_id: str = "usuario-uno",
    sesion_id: str = "sesion-uno",
    vigencia: VigenciaDeSesion | None = None,
    control: ControlDePrueba | None = None,
) -> SesionEnVivo:
    return SesionEnVivo(
        sesion_id=sesion_id,
        usuario_id=usuario_id,
        roles=(rol,),
        area_id=area_id,
        vigencia=vigencia or una_vigencia(),
        control=control or ControlDePrueba(),
    )


class CategoriasEnMemoria:
    def __init__(self, categorias: CategoriasPorRol | None = None) -> None:
        self.categorias = categorias if categorias is not None else CATEGORIAS
        self.llamadas = 0
        self.falla: Exception | None = None

    async def categorias_por_rol(self) -> CategoriasPorRol:
        self.llamadas += 1
        if self.falla is not None:
            raise self.falla
        return self.categorias


class SeguimientoEnMemoria:
    def __init__(self) -> None:
        self.control = ControlDePrueba()
        self.verificaciones: list[str] = []
        self.actualizadas: list[SesionEnVivo] = []
        self.sesiones_invalidadas: list[str] = []
        self.usuarios_invalidados: list[str] = []

    def iniciar_verificacion(self, sesion_id: str) -> ControlDePrueba:
        self.verificaciones.append(sesion_id)
        return self.control

    def actualizar_sesion(self, sesion: SesionEnVivo) -> None:
        self.actualizadas.append(sesion)

    def invalidar_sesion(self, sesion_id: str) -> None:
        self.sesiones_invalidadas.append(sesion_id)

    def invalidar_usuario(self, usuario_id: str) -> None:
        self.usuarios_invalidados.append(usuario_id)
