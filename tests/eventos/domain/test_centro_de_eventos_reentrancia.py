from collections.abc import Callable
from datetime import timedelta

from app.enums.evento_nombre import EventoNombre
from app.enums.motivo_de_cierre import MotivoDeCierre
from app.eventos.domain.centro_de_eventos import CentroDeEventos
from tests.helpers.eventos_en_memoria import (
    INICIO,
    SuscriptorFalso,
    TiempoManual,
    una_sesion_en_vivo,
    una_vigencia,
)
from tests.helpers.registro_en_memoria import RegistroEnMemoria


class SuscriptorReactivo(SuscriptorFalso):
    def __init__(self, reaccion: Callable[[], None], cuando: str) -> None:
        super().__init__()
        self._reaccion = reaccion
        self._cuando = cuando

    def cerrar(self, motivo: MotivoDeCierre) -> None:
        super().cerrar(motivo)
        if self._cuando == "cerrar":
            self._reaccion()

    def latido(self) -> None:
        super().latido()
        if self._cuando == "latido":
            self._reaccion()

    def enviar(self, evento: EventoNombre) -> None:
        super().enviar(evento)
        if self._cuando == "enviar":
            self._reaccion()


def _centro() -> tuple[CentroDeEventos, TiempoManual]:
    tiempo = TiempoManual()
    return CentroDeEventos(tiempo, RegistroEnMemoria()), tiempo


def test_invalidar_una_sesion_no_toca_las_verificaciones_de_otra() -> None:
    centro, _ = _centro()
    ajena = centro.iniciar_verificacion("sesion-ajena")

    centro.invalidar_sesion("sesion-otra")

    assert ajena.vigente() is True


def test_invalidar_al_usuario_de_una_verificacion_ya_identificada_la_invalida() -> None:
    centro, _ = _centro()
    identificada = centro.iniciar_verificacion("sesion-uno")
    otra_persona = centro.iniciar_verificacion("sesion-dos")
    identificada.identificar("uno")
    otra_persona.identificar("dos")

    centro.invalidar_usuario("uno")

    assert (identificada.vigente(), otra_persona.vigente()) == (False, True)


def test_si_un_suscriptor_cierra_a_otro_al_apagar_el_segundo_no_se_cierra_dos_veces() -> None:
    centro, _ = _centro()
    segundo = SuscriptorFalso()
    primero = SuscriptorReactivo(lambda: centro.invalidar_usuario("segundo"), "cerrar")
    centro.suscribir(una_sesion_en_vivo(usuario_id="primero", sesion_id="s1"), primero)
    centro.suscribir(una_sesion_en_vivo(usuario_id="segundo", sesion_id="s2"), segundo)

    centro.cerrar_todo()

    assert primero.cierres == [MotivoDeCierre.APAGADO]
    assert segundo.cierres == [MotivoDeCierre.SESION_INVALIDA]
    assert centro.conectados == 0


def test_si_un_latido_provoca_la_baja_de_otro_cliente_ese_cliente_ya_no_recibe_el_latido() -> None:
    centro, tiempo = _centro()
    segundo = SuscriptorFalso()
    primero = SuscriptorReactivo(lambda: centro.invalidar_usuario("segundo"), "latido")
    centro.suscribir(una_sesion_en_vivo(usuario_id="primero", sesion_id="s1"), primero)
    centro.suscribir(una_sesion_en_vivo(usuario_id="segundo", sesion_id="s2"), segundo)

    tiempo.avanzar(25)

    assert primero.latidos == 1
    assert (segundo.latidos, segundo.cierres) == (0, [MotivoDeCierre.SESION_INVALIDA])


def test_una_sesion_invalidada_dos_veces_a_la_vez_cierra_a_cada_cliente_una_sola_vez() -> None:
    centro, _ = _centro()
    segundo = SuscriptorFalso()
    primero = SuscriptorReactivo(lambda: centro.invalidar_sesion("misma"), "enviar")
    centro.suscribir(una_sesion_en_vivo(sesion_id="misma"), primero)
    centro.suscribir(una_sesion_en_vivo(sesion_id="misma"), segundo)

    centro.invalidar_sesion("misma")

    assert primero.enviados == [EventoNombre.SESION]
    assert segundo.enviados == [EventoNombre.SESION]
    assert (primero.cierres, segundo.cierres) == ([MotivoDeCierre.SESION_INVALIDA], [MotivoDeCierre.SESION_INVALIDA])


def test_si_el_temporizador_salta_antes_de_tiempo_se_vuelve_a_programar_sin_cerrar() -> None:
    centro, tiempo = _centro()
    vigencia = una_vigencia(inactiva_en=INICIO + timedelta(seconds=10))
    cliente = SuscriptorFalso()
    centro.suscribir(una_sesion_en_vivo(vigencia=vigencia), cliente)
    antes = tiempo.pendientes

    tiempo.disparar_sin_avanzar()

    assert (cliente.cierres, tiempo.pendientes) == ([], antes)
    tiempo.avanzar(10)
    assert cliente.cierres == [MotivoDeCierre.SESION_INVALIDA]
