from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.shared.rate_limit import RateLimitPolicies
    from app.shared.session_cookie import SessionCookieConfig
    from app.shared.token_bucket import BucketPolicy


@dataclass(frozen=True, slots=True)
class HttpSecurity:
    cookies: SessionCookieConfig
    rate_limits: RateLimitPolicies
    login_by_email: BucketPolicy
    login_by_ip: BucketPolicy
    session_max_age_seconds: int
    allowed_origins: tuple[str, ...] = ()
    trust_proxy: bool = False
