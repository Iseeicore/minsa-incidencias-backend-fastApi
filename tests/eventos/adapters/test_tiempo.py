import asyncio
from datetime import UTC, datetime

from app.eventos.adapters.tiempo import TiempoAsyncio

PASO = 0.02


async def test_ahora_es_la_hora_actual_con_zona_horaria() -> None:
    antes = datetime.now(UTC)

    ahora = TiempoAsyncio().ahora()

    assert antes <= ahora <= datetime.now(UTC)


async def test_programar_ejecuta_una_vez_y_se_puede_cancelar() -> None:
    llamadas: list[str] = []
    tiempo = TiempoAsyncio()
    tiempo.programar(lambda: llamadas.append("a"), PASO)
    cancelar = tiempo.programar(lambda: llamadas.append("b"), PASO)
    cancelar()

    await asyncio.sleep(PASO * 4)

    assert llamadas == ["a"]


async def test_repetir_sigue_ejecutando_hasta_que_se_cancela() -> None:
    llamadas: list[int] = []
    cancelar = TiempoAsyncio().repetir(lambda: llamadas.append(1), PASO)

    await asyncio.sleep(PASO * 5.5)
    cancelar()
    detenido = len(llamadas)
    await asyncio.sleep(PASO * 3)

    assert detenido >= 3
    assert len(llamadas) == detenido
