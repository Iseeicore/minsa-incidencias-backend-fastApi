from dataclasses import dataclass
from typing import TYPE_CHECKING

from starlette.datastructures import MutableHeaders
from starlette.requests import Request

from app.constants.http import (
    RATE_LIMIT_LIMIT_HEADER,
    RATE_LIMIT_REMAINING_HEADER,
    RETRY_AFTER_HEADER,
    SESSION_STATE_KEY,
)
from app.errors.demasiadas_peticiones import DemasiadasPeticiones
from app.shared.client_ip import client_ip
from app.shared.http_errors import domain_error_response
from app.shared.route_path import is_logout
from app.shared.sesion import SesionActual

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from app.shared.clock import Clock
    from app.shared.token_bucket import BucketPolicy, TakeResult, TokenBucketLimiter


@dataclass(frozen=True, slots=True)
class RateLimitPolicies:
    authenticated: BucketPolicy
    anonymous: BucketPolicy


@dataclass(frozen=True, slots=True)
class RateLimitTarget:
    key: str
    policy: BucketPolicy


def general_target(scope: Scope, policies: RateLimitPolicies, *, trust_proxy: bool) -> RateLimitTarget:
    sesion = scope.get("state", {}).get(SESSION_STATE_KEY)
    if isinstance(sesion, SesionActual):
        return RateLimitTarget(f"usuario:{sesion.usuario_id}", policies.authenticated)
    return RateLimitTarget(f"ip:{client_ip(scope, trust_proxy=trust_proxy)}", policies.anonymous)


def rate_limit_headers(result: TakeResult) -> dict[str, str]:
    return {RATE_LIMIT_LIMIT_HEADER: str(result.limit), RATE_LIMIT_REMAINING_HEADER: str(result.remaining)}


class RateLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        limiter: TokenBucketLimiter,
        policies: RateLimitPolicies,
        clock: Clock,
        *,
        trust_proxy: bool,
    ) -> None:
        self._app = app
        self._limiter = limiter
        self._policies = policies
        self._clock = clock
        self._trust_proxy = trust_proxy

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or is_logout(scope):
            await self._app(scope, receive, send)
            return
        target = general_target(scope, self._policies, trust_proxy=self._trust_proxy)
        result = self._limiter.take(target.key, target.policy)
        headers = rate_limit_headers(result)
        if not result.allowed:
            headers[RETRY_AFTER_HEADER] = str(result.retry_after_seconds)
            response = domain_error_response(Request(scope), self._clock, DemasiadasPeticiones(), headers)
            await response(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                for name, value in headers.items():
                    response_headers[name] = value
            await send(message)

        await self._app(scope, receive, send_with_headers)
