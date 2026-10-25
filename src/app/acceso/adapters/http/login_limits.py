from typing import TYPE_CHECKING

from fastapi import Request, Response  # noqa: TC002

from app.constants.sesion import MAX_EMAIL_LENGTH
from app.shared.client_ip import client_ip
from app.shared.rate_limit import rate_limit_headers, rate_limited

if TYPE_CHECKING:
    from app.shared.http_security import HttpSecurity
    from app.shared.token_bucket import BucketPolicy, TokenBucketLimiter


class LoginLimits:
    def __init__(self, limiter: TokenBucketLimiter, security: HttpSecurity) -> None:
        self._limiter = limiter
        self._security = security

    async def __call__(self, request: Request, response: Response) -> None:
        ip = client_ip(request.scope, trust_proxy=self._security.trust_proxy)
        self._take(f"login-ip:{ip}", self._security.login_by_ip, response)
        correo = await self._correo_del_cuerpo(request)
        key = f"login:{correo}" if correo else f"login-sin-correo:{ip}"
        self._take(key, self._security.login_by_email, response)

    def _take(self, key: str, policy: BucketPolicy, response: Response) -> None:
        result = self._limiter.take(key, policy)
        if not result.allowed:
            raise rate_limited(result)
        response.headers.update(rate_limit_headers(result))

    async def _correo_del_cuerpo(self, request: Request) -> str | None:
        try:
            cuerpo = await request.json()
        except ValueError:
            return None
        valor = cuerpo.get("correo") if isinstance(cuerpo, dict) else None
        if not isinstance(valor, str):
            return None
        return valor.strip().lower()[:MAX_EMAIL_LENGTH] or None
