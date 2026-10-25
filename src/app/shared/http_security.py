from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.shared.rate_limit import RateLimitPolicies
    from app.shared.session_cookie import SessionCookieConfig


@dataclass(frozen=True, slots=True)
class HttpSecurity:
    cookies: SessionCookieConfig
    rate_limits: RateLimitPolicies
    allowed_origins: tuple[str, ...] = ()
    trust_proxy: bool = False
