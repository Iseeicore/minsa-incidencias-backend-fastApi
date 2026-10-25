import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.shared.token_bucket import TokenBucketLimiter


async def sweep_forever(limiter: TokenBucketLimiter, interval_seconds: float) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        limiter.sweep()
