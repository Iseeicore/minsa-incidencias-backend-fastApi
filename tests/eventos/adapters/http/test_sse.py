from app.enums.evento_nombre import EventoNombre
from app.enums.motivo_de_cierre import MotivoDeCierre
from app.eventos.adapters.http.sse import SuscriptorSse


class _Baja:
    def __init__(self) -> None:
        self.llamadas = 0

    def __call__(self) -> None:
        self.llamadas += 1


async def test_el_flujo_anuncia_el_reintento_y_entrega_los_trozos_en_orden_hasta_el_cierre() -> None:
    suscriptor = SuscriptorSse()
    baja = _Baja()
    suscriptor.enviar(EventoNombre.CAMBIO)
    suscriptor.latido()
    suscriptor.enviar(EventoNombre.SESION)
    suscriptor.cerrar(MotivoDeCierre.SESION_INVALIDA)

    trozos = [trozo async for trozo in suscriptor.flujo(baja)]

    assert "".join(trozos) == "retry: 5000\n\nevent: cambio\ndata: {}\n\n: latido\n\nevent: sesion\ndata: {}\n\n"
    assert baja.llamadas == 1


async def test_escribir_despues_de_cerrar_no_falla_ni_agrega_nada() -> None:
    suscriptor = SuscriptorSse()
    suscriptor.cerrar(MotivoDeCierre.APAGADO)

    suscriptor.enviar(EventoNombre.CAMBIO)
    suscriptor.latido()
    suscriptor.cerrar(MotivoDeCierre.CLIENTE)
    trozos = [trozo async for trozo in suscriptor.flujo(_Baja())]

    assert trozos == ["retry: 5000\n\n"]


async def test_si_el_cliente_se_va_a_mitad_del_flujo_se_da_de_baja() -> None:
    suscriptor = SuscriptorSse()
    baja = _Baja()
    flujo = suscriptor.flujo(baja)

    assert await anext(flujo) == "retry: 5000\n\n"
    await flujo.aclose()

    assert baja.llamadas == 1
