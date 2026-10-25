import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants.limits import MS_PER_SECOND, RATE_LIMIT_MAX_KEYS
from app.errors.limite_de_claves_invalido import LimiteDeClavesInvalido

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class BucketPolicy:
    capacity: int
    window_seconds: int


@dataclass(frozen=True, slots=True)
class TakeResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


@dataclass(slots=True)
class _Bucket:
    tokens: float
    updated_at: float
    full_at: float


def monotonic_ms() -> float:
    return time.monotonic() * MS_PER_SECOND


class TokenBucketLimiter:
    def __init__(self, now: Callable[[], float] = monotonic_ms, max_keys: int = RATE_LIMIT_MAX_KEYS) -> None:
        if max_keys < 1:
            raise LimiteDeClavesInvalido(max_keys)
        self._now = now
        self._max_keys = max_keys
        self._buckets: dict[str, _Bucket] = {}

    @property
    def size(self) -> int:
        return len(self._buckets)

    def take(self, key: str, policy: BucketPolicy) -> TakeResult:
        refill_per_ms = policy.capacity / (policy.window_seconds * MS_PER_SECOND)
        now = self._now()
        bucket = self._buckets.get(key)

        if bucket is None and len(self._buckets) >= self._max_keys:
            self.sweep()
            if len(self._buckets) >= self._max_keys:
                return TakeResult(
                    allowed=False,
                    limit=policy.capacity,
                    remaining=0,
                    retry_after_seconds=self._retry_after_saturation(now),
                )

        if bucket is None:
            bucket = _Bucket(float(policy.capacity), now, now)

        bucket.tokens = min(policy.capacity, bucket.tokens + (now - bucket.updated_at) * refill_per_ms)
        bucket.updated_at = now

        allowed = bucket.tokens >= 1
        if allowed:
            bucket.tokens -= 1
        bucket.full_at = now + (policy.capacity - bucket.tokens) / refill_per_ms
        self._buckets[key] = bucket

        retry_after = 0 if allowed else math.ceil((1 - bucket.tokens) / refill_per_ms / MS_PER_SECOND)
        return TakeResult(allowed, policy.capacity, math.floor(bucket.tokens), retry_after)

    def _retry_after_saturation(self, now: float) -> int:
        next_release = min((bucket.full_at for bucket in self._buckets.values()), default=math.inf)
        if math.isinf(next_release):
            return 1
        return max(1, math.ceil((next_release - now) / MS_PER_SECOND))

    def sweep(self) -> int:
        now = self._now()
        expired = [key for key, bucket in self._buckets.items() if bucket.full_at <= now]
        for key in expired:
            del self._buckets[key]
        return len(expired)
