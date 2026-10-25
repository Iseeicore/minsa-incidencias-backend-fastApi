import asyncio
from contextlib import suppress

from app.shared.limiter_sweeper import sweep_forever
from app.shared.token_bucket import BucketPolicy, TokenBucketLimiter

POLITICA = BucketPolicy(capacity=1, window_seconds=1)


async def test_el_barredor_elimina_las_cubetas_llenas_cada_intervalo() -> None:
    ahora = [0.0]
    limitador = TokenBucketLimiter(lambda: ahora[0])
    limitador.take("a", POLITICA)
    ahora[0] += 5_000

    tarea = asyncio.create_task(sweep_forever(limitador, interval_seconds=0.01))
    await asyncio.sleep(0.05)
    tarea.cancel()
    with suppress(asyncio.CancelledError):
        await tarea

    assert limitador.size == 0
