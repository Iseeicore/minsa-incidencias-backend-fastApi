import asyncio

from app.shared.ciclo_periodico import CicloPeriodico, ProcesosDeFondo, repetir_hasta_parar

INTERVALO_CORTO = 0.01


class _Contador:
    def __init__(self, *, parar_al_llegar_a: int | None = None, parar: asyncio.Event | None = None) -> None:
        self.llamadas = 0
        self._parar_al_llegar_a = parar_al_llegar_a
        self._parar = parar

    async def __call__(self) -> None:
        self.llamadas += 1
        if self._parar is not None and self.llamadas == self._parar_al_llegar_a:
            self._parar.set()


async def test_una_sola_vez_ejecuta_el_ciclo_y_termina_sin_esperar_el_intervalo() -> None:
    contador = _Contador()

    await asyncio.wait_for(repetir_hasta_parar(contador, asyncio.Event(), 3600, una_vez=True), timeout=2)

    assert contador.llamadas == 1


async def test_si_ya_se_pidio_parar_no_se_ejecuta_ningun_ciclo() -> None:
    parar = asyncio.Event()
    parar.set()
    contador = _Contador()

    await repetir_hasta_parar(contador, parar, INTERVALO_CORTO)

    assert contador.llamadas == 0


async def test_repite_el_ciclo_cada_intervalo_hasta_que_se_pide_parar() -> None:
    parar = asyncio.Event()
    contador = _Contador(parar_al_llegar_a=3, parar=parar)

    await asyncio.wait_for(repetir_hasta_parar(contador, parar, INTERVALO_CORTO), timeout=2)

    assert contador.llamadas == 3


async def test_pedir_parar_durante_la_espera_corta_el_intervalo() -> None:
    parar = asyncio.Event()
    contador = _Contador()
    tarea = asyncio.create_task(repetir_hasta_parar(contador, parar, 3600))
    await asyncio.sleep(0.05)

    parar.set()
    await asyncio.wait_for(tarea, timeout=2)

    assert contador.llamadas == 1


async def test_el_ciclo_periodico_arranca_de_inmediato_y_detener_espera_al_ciclo_en_curso() -> None:
    entro = asyncio.Event()
    liberar = asyncio.Event()
    terminados: list[str] = []

    async def ciclo() -> None:
        entro.set()
        await liberar.wait()
        terminados.append("ciclo")

    periodico = CicloPeriodico(ciclo, 3600)
    periodico.iniciar()
    periodico.iniciar()
    await asyncio.wait_for(entro.wait(), timeout=2)
    detencion = asyncio.create_task(periodico.detener())
    await asyncio.sleep(0.02)

    assert not detencion.done()
    liberar.set()
    await asyncio.wait_for(detencion, timeout=2)
    assert terminados == ["ciclo"]


async def test_detener_un_ciclo_que_nunca_arranco_no_falla() -> None:
    await CicloPeriodico(_Contador(), INTERVALO_CORTO).detener()


async def test_los_procesos_de_fondo_inician_y_detienen_todos_sus_ciclos() -> None:
    primero, segundo = _Contador(), _Contador()
    procesos = ProcesosDeFondo([CicloPeriodico(primero, 3600), CicloPeriodico(segundo, 3600)])

    procesos.iniciar()
    await asyncio.sleep(0.05)
    await asyncio.wait_for(procesos.detener(), timeout=2)

    assert (primero.llamadas, segundo.llamadas) == (1, 1)
