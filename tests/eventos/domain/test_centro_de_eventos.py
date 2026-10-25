from dataclasses import replace
from datetime import timedelta
from itertools import count
from typing import TYPE_CHECKING

import pytest

from app.constants.eventos import (
    EVENTOS_AGRUPADO_SEGUNDOS,
    EVENTOS_LATIDO_SEGUNDOS,
    EVENTOS_MAX_POR_USUARIO,
    EVENTOS_MAX_TOTAL,
)
from app.enums.evento_nombre import EventoNombre
from app.enums.motivo_de_cierre import MotivoDeCierre
from app.enums.rol_codigo import RolCodigo
from app.errors.demasiadas_conexiones import DemasiadasConexiones
from app.errors.sesion_invalida import SesionInvalida
from app.eventos.domain.cambio_de_incidencia import CambioDeIncidencia
from app.eventos.domain.centro_de_eventos import CentroDeEventos, enmascarar_identificador
from app.shared.sesion import SesionEnVivo
from tests.helpers.eventos_en_memoria import (
    CATEGORIAS,
    CORRUPCION,
    INICIO,
    QUEJA,
    ControlDePrueba,
    SuscriptorFalso,
    TiempoManual,
    una_sesion_en_vivo,
    una_vigencia,
)
from tests.helpers.registro_en_memoria import RegistroEnMemoria

if TYPE_CHECKING:
    from collections.abc import Callable

AREA_OTRANS = 10
AREA_A = 21
AREA_B = 22
CAMBIO = EventoNombre.CAMBIO
SESION = EventoNombre.SESION
numero = count(1)


class Escenario:
    def __init__(self) -> None:
        self.tiempo = TiempoManual()
        self.registro = RegistroEnMemoria()
        self.centro = CentroDeEventos(self.tiempo, self.registro)

    def conectar(self, sesion: SesionEnVivo) -> tuple[SuscriptorFalso, Callable[[], None]]:
        suscriptor = SuscriptorFalso()
        return suscriptor, self.centro.suscribir(sesion, suscriptor)

    def conectar_a(
        self, rol: str, area_id: int | None, usuario_id: str | None = None
    ) -> tuple[SuscriptorFalso, Callable[[], None]]:
        indice = next(numero)
        return self.conectar(
            una_sesion_en_vivo(rol, area_id, usuario_id=usuario_id or f"usuario-{indice}", sesion_id=f"sesion-{indice}")
        )


def en_area(area: int, categoria: int) -> CambioDeIncidencia:
    return CambioDeIncidencia(area, area, categoria, categoria)


def test_un_cambio_general_llega_a_todos_los_conectados_tras_la_ventana_de_agrupacion() -> None:
    escenario = Escenario()
    establecimiento, _ = escenario.conectar_a(RolCodigo.ESTABLECIMIENTO, AREA_A)
    otrans, _ = escenario.conectar_a(RolCodigo.OTRANS, AREA_OTRANS)

    escenario.centro.publicar_cambio()
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)

    assert establecimiento.enviados == [CAMBIO]
    assert otrans.enviados == [CAMBIO]


def test_una_publicacion_dirigida_conserva_el_alcance_por_area_y_categoria() -> None:
    escenario = Escenario()
    del_a, _ = escenario.conectar_a(RolCodigo.ESTABLECIMIENTO, AREA_A)
    del_b, _ = escenario.conectar_a(RolCodigo.GESTOR, AREA_B)
    otrans, _ = escenario.conectar_a(RolCodigo.OTRANS, AREA_OTRANS)
    admin, _ = escenario.conectar_a(RolCodigo.ADMINISTRADOR, None)

    escenario.centro.publicar([CambioDeIncidencia(AREA_A, AREA_B, QUEJA, QUEJA)], CATEGORIAS)
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)

    for suscriptor in (del_a, del_b, otrans, admin):
        assert suscriptor.enviados == [CAMBIO]


def test_una_publicacion_de_corrupcion_llega_a_otrans_y_no_al_establecimiento() -> None:
    escenario = Escenario()
    establecimiento, _ = escenario.conectar_a(RolCodigo.ESTABLECIMIENTO, AREA_A)
    otrans, _ = escenario.conectar_a(RolCodigo.OTRANS, AREA_OTRANS)

    escenario.centro.publicar([en_area(AREA_OTRANS, CORRUPCION)], CATEGORIAS)
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)

    assert otrans.enviados == [CAMBIO]
    assert establecimiento.enviados == []


def test_sin_clientes_o_sin_cambios_publicar_no_hace_nada() -> None:
    escenario = Escenario()
    escenario.centro.publicar([en_area(AREA_A, QUEJA)], CATEGORIAS)
    admin, _ = escenario.conectar_a(RolCodigo.ADMINISTRADOR, None)

    escenario.centro.publicar([], CATEGORIAS)
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)

    assert admin.enviados == []


def test_cincuenta_cambios_se_agrupan_en_un_solo_evento_y_luego_queda_inactivo() -> None:
    escenario = Escenario()
    admin, _ = escenario.conectar_a(RolCodigo.ADMINISTRADOR, None)

    for _ in range(51):
        escenario.centro.publicar_cambio()
    assert admin.enviados == []
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)
    escenario.tiempo.avanzar(EVENTOS_LATIDO_SEGUNDOS * 3)

    assert admin.enviados == [CAMBIO]


def test_el_paso_del_tiempo_solo_envia_latidos() -> None:
    escenario = Escenario()
    cliente, _ = escenario.conectar_a(RolCodigo.GESTOR, AREA_A)

    escenario.tiempo.avanzar(EVENTOS_LATIDO_SEGUNDOS * 12)

    assert (cliente.latidos, cliente.enviados) == (12, [])


def test_el_latido_se_detiene_al_irse_el_ultimo_cliente_y_no_quedan_temporizadores() -> None:
    escenario = Escenario()
    _, primero = escenario.conectar_a(RolCodigo.GESTOR, AREA_A)
    _, segundo = escenario.conectar_a(RolCodigo.OTRANS, AREA_OTRANS)
    assert escenario.tiempo.pendientes == 3

    primero()
    assert escenario.tiempo.pendientes == 2
    segundo()
    assert escenario.tiempo.pendientes == 0


def test_darse_de_baja_dos_veces_es_inofensivo_y_libera_el_control_de_la_sesion() -> None:
    escenario = Escenario()
    control = ControlDePrueba()
    _, baja = escenario.conectar(una_sesion_en_vivo(control=control))

    baja()
    baja()

    assert control.activo is False
    assert escenario.centro.conectados == 0


def test_hay_un_limite_de_flujos_por_usuario() -> None:
    escenario = Escenario()
    for _ in range(EVENTOS_MAX_POR_USUARIO):
        escenario.conectar_a(RolCodigo.GESTOR, AREA_A, "usuario-con-muchas-pestanas")

    with pytest.raises(DemasiadasConexiones):
        escenario.conectar_a(RolCodigo.GESTOR, AREA_A, "usuario-con-muchas-pestanas")

    assert escenario.centro.conectados == EVENTOS_MAX_POR_USUARIO


def test_hay_un_limite_total_de_flujos() -> None:
    escenario = Escenario()
    for indice in range(EVENTOS_MAX_TOTAL):
        escenario.conectar_a(RolCodigo.GESTOR, AREA_A, f"usuario-{indice}-total")

    with pytest.raises(DemasiadasConexiones):
        escenario.conectar_a(RolCodigo.GESTOR, AREA_A, "uno-mas")

    assert escenario.centro.conectados == EVENTOS_MAX_TOTAL


def test_al_apagar_cierra_todos_los_flujos_y_limpia_los_temporizadores() -> None:
    escenario = Escenario()
    a, _ = escenario.conectar_a(RolCodigo.ESTABLECIMIENTO, AREA_A)
    b, _ = escenario.conectar_a(RolCodigo.ADMINISTRADOR, None)

    escenario.centro.cerrar_todo()

    assert a.cierres == [MotivoDeCierre.APAGADO]
    assert b.cierres == [MotivoDeCierre.APAGADO]
    assert (escenario.centro.conectados, escenario.tiempo.pendientes) == (0, 0)


def test_tras_apagar_no_se_aceptan_suscripciones_ni_verificaciones_vigentes() -> None:
    escenario = Escenario()
    pendiente = escenario.centro.iniciar_verificacion("sesion-previa")

    escenario.centro.cerrar_todo()
    tardia = escenario.centro.iniciar_verificacion("sesion-tardia")

    assert (pendiente.vigente(), tardia.vigente()) == (False, False)
    with pytest.raises(SesionInvalida):
        escenario.conectar_a(RolCodigo.GESTOR, AREA_A)


def test_al_vencer_la_inactividad_avisa_la_sesion_y_cierra() -> None:
    escenario = Escenario()
    vigencia = una_vigencia(inactiva_en=INICIO + timedelta(seconds=2))
    cliente, _ = escenario.conectar(una_sesion_en_vivo(vigencia=vigencia))

    escenario.tiempo.avanzar(2)

    assert cliente.enviados == [SESION]
    assert cliente.cierres == [MotivoDeCierre.SESION_INVALIDA]
    assert (escenario.centro.conectados, escenario.tiempo.pendientes) == (0, 0)


def test_no_se_acepta_una_suscripcion_cuya_vigencia_ya_vencio() -> None:
    escenario = Escenario()
    vencida = una_sesion_en_vivo(vigencia=una_vigencia(vence_en=INICIO, inactiva_en=INICIO + timedelta(hours=1)))

    with pytest.raises(SesionInvalida):
        escenario.conectar(vencida)

    assert escenario.centro.conectados == 0


def test_revocar_una_sesion_cierra_todas_sus_conexiones_pero_no_otras_sesiones_del_mismo_usuario() -> None:
    escenario = Escenario()
    datos = una_sesion_en_vivo(usuario_id="usuario-uno", sesion_id="sesion-revocada")
    primero, _ = escenario.conectar(datos)
    segundo, _ = escenario.conectar(replace(datos, control=ControlDePrueba()))
    otra, _ = escenario.conectar(una_sesion_en_vivo(usuario_id="usuario-uno", sesion_id="sesion-otra"))
    escenario.centro.publicar_cambio()

    escenario.centro.invalidar_sesion("sesion-revocada")
    escenario.centro.invalidar_sesion("sesion-revocada")
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)

    for cliente in (primero, segundo):
        assert (cliente.enviados, cliente.cierres) == ([SESION], [MotivoDeCierre.SESION_INVALIDA])
    assert (otra.enviados, otra.cierres) == ([CAMBIO], [])


def test_invalidar_al_usuario_cierra_sus_sesiones_sin_afectar_a_otra_persona() -> None:
    escenario = Escenario()
    propias = [escenario.conectar_a(RolCodigo.GESTOR, AREA_A, "uno")[0] for _ in range(2)]
    ajena, _ = escenario.conectar_a(RolCodigo.GESTOR, AREA_A, "otro")

    escenario.centro.invalidar_usuario("uno")

    for cliente in propias:
        assert cliente.cierres == [MotivoDeCierre.SESION_INVALIDA]
    assert ajena.cierres == []
    assert escenario.centro.conectados == 1


@pytest.mark.parametrize("tipo", ["sesion", "usuario"])
def test_rechaza_una_suscripcion_tardia_invalidada_durante_la_verificacion(tipo: str) -> None:
    escenario = Escenario()
    control = escenario.centro.iniciar_verificacion("sesion-uno")
    if tipo == "sesion":
        escenario.centro.invalidar_sesion("sesion-uno")
    else:
        escenario.centro.invalidar_usuario("usuario-uno")

    assert control.identificar("usuario-uno") is False
    sesion = replace(una_sesion_en_vivo(usuario_id="usuario-uno", sesion_id="sesion-uno"), control=control)
    with pytest.raises(SesionInvalida):
        escenario.conectar(sesion)
    control.liberar()
    assert (escenario.centro.conectados, escenario.tiempo.pendientes) == (0, 0)


def test_la_revocacion_de_otra_persona_durante_la_verificacion_no_invalida_la_identidad_comprobada() -> None:
    escenario = Escenario()
    control = escenario.centro.iniciar_verificacion("sesion-uno")

    escenario.centro.invalidar_usuario("otro")

    assert control.identificar("uno") is True
    control.liberar()
    assert control.vigente() is False


def test_una_verificacion_que_cambia_de_usuario_se_invalida() -> None:
    escenario = Escenario()
    control = escenario.centro.iniciar_verificacion("sesion-uno")

    assert control.identificar("uno") is True
    assert control.identificar("dos") is False
    assert control.vigente() is False


def test_la_actividad_renueva_la_inactividad_sin_retroceder_ni_ampliar_el_plazo_absoluto() -> None:
    escenario = Escenario()
    vigencia = una_vigencia(vence_en=INICIO + timedelta(seconds=6), inactiva_en=INICIO + timedelta(seconds=2))
    datos = una_sesion_en_vivo(vigencia=vigencia)
    cliente, _ = escenario.conectar(datos)
    escenario.tiempo.avanzar(1)

    escenario.centro.actualizar_sesion(
        replace(
            datos,
            control=ControlDePrueba(),
            vigencia=una_vigencia(inactiva_en=INICIO + timedelta(seconds=9)),
        )
    )
    escenario.centro.actualizar_sesion(replace(datos, control=ControlDePrueba()))
    escenario.tiempo.avanzar(4.999)

    assert cliente.cierres == []
    escenario.tiempo.avanzar(0.001)
    assert (cliente.enviados, cliente.cierres) == ([SESION], [MotivoDeCierre.SESION_INVALIDA])


def test_actualizar_con_una_respuesta_liberada_no_renueva_el_plazo_del_cliente() -> None:
    escenario = Escenario()
    vigencia = una_vigencia(inactiva_en=INICIO + timedelta(seconds=1))
    datos = una_sesion_en_vivo(vigencia=vigencia)
    cliente, _ = escenario.conectar(datos)
    liberada = ControlDePrueba()
    liberada.liberar()

    escenario.centro.actualizar_sesion(replace(datos, control=liberada, vigencia=una_vigencia()))
    escenario.tiempo.avanzar(1)

    assert cliente.cierres == [MotivoDeCierre.SESION_INVALIDA]


def test_actualizar_cambia_los_roles_y_el_area_con_los_que_se_reparten_los_avisos() -> None:
    escenario = Escenario()
    datos = una_sesion_en_vivo(RolCodigo.ESTABLECIMIENTO, AREA_A)
    cliente, _ = escenario.conectar(datos)

    escenario.centro.actualizar_sesion(
        replace(datos, control=ControlDePrueba(), roles=(RolCodigo.OTRANS,), area_id=None)
    )
    escenario.centro.publicar([en_area(AREA_OTRANS, CORRUPCION)], CATEGORIAS)
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)

    assert cliente.enviados == [CAMBIO]


def test_actualizar_una_sesion_ajena_no_toca_a_los_conectados() -> None:
    escenario = Escenario()
    cliente, _ = escenario.conectar(una_sesion_en_vivo(sesion_id="sesion-uno"))

    escenario.centro.actualizar_sesion(una_sesion_en_vivo(sesion_id="sesion-otra"))
    escenario.tiempo.avanzar(1)

    assert (cliente.enviados, cliente.cierres, escenario.centro.conectados) == ([], [], 1)


def test_el_registro_informa_cada_apertura_y_cierre_con_el_usuario_enmascarado() -> None:
    escenario = Escenario()
    _, baja = escenario.conectar(una_sesion_en_vivo(usuario_id="0199a2b4-7c3d-aaaa"))

    baja()

    assert escenario.registro.eventos == [
        ("info", "eventos: flujo abierto", {"usuario": "••••aaaa", "conectados": 1}),
        ("info", "eventos: flujo cerrado", {"usuario": "••••aaaa", "motivo": "cliente", "conectados": 0}),
    ]


@pytest.mark.parametrize(("identificador", "esperado"), [("1234", "••••"), ("", "••••"), ("abcde", "••••bcde")])
def test_enmascarar_deja_solo_los_ultimos_cuatro_caracteres_si_hay_mas(identificador: str, esperado: str) -> None:
    assert enmascarar_identificador(identificador) == esperado


def test_un_cliente_cuya_sesion_se_invalida_entre_avisos_recibe_sesion_y_no_cambio() -> None:
    escenario = Escenario()
    control = ControlDePrueba()
    cliente, _ = escenario.conectar(una_sesion_en_vivo(control=control))
    escenario.centro.publicar_cambio()
    control.activo = False

    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)

    assert (cliente.enviados, cliente.cierres) == ([SESION], [MotivoDeCierre.SESION_INVALIDA])


def test_el_latido_comprueba_la_sesion_de_cada_cliente() -> None:
    escenario = Escenario()
    control = ControlDePrueba()
    cliente, _ = escenario.conectar(una_sesion_en_vivo(control=control))
    control.activo = False

    escenario.tiempo.avanzar(EVENTOS_LATIDO_SEGUNDOS)

    assert (cliente.latidos, cliente.cierres) == (0, [MotivoDeCierre.SESION_INVALIDA])


def test_el_vencimiento_se_reprograma_si_la_vigencia_se_extendio_antes_de_cumplirse() -> None:
    escenario = Escenario()
    datos = una_sesion_en_vivo(vigencia=una_vigencia(inactiva_en=INICIO + timedelta(seconds=3)))
    cliente, _ = escenario.conectar(datos)
    escenario.tiempo.avanzar(1)
    escenario.centro.actualizar_sesion(
        replace(datos, control=ControlDePrueba(), vigencia=una_vigencia(inactiva_en=INICIO + timedelta(seconds=10)))
    )

    escenario.tiempo.avanzar(3)

    assert cliente.cierres == []
    escenario.tiempo.avanzar(6)
    assert cliente.cierres == [MotivoDeCierre.SESION_INVALIDA]
