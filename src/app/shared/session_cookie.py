from dataclasses import dataclass
from email.utils import format_datetime
from typing import TYPE_CHECKING
from urllib.parse import quote
from uuid import UUID

from app.constants.sesion import (
    COOKIE_PATH,
    COOKIE_SAME_SITE,
    EPOCH_EXPIRES,
    HOST_SESSION_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    SIGNED_COOKIE_PREFIX,
    UUID_EXTREMES,
    UUID_VERSIONS,
)
from app.shared.signed_cookie import read_signed, sign

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class SessionCookieConfig:
    secrets: tuple[str, ...]
    production: bool

    @property
    def name(self) -> str:
        return HOST_SESSION_COOKIE_NAME if self.production else SESSION_COOKIE_NAME


def _is_session_id(value: str) -> bool:
    try:
        parsed = UUID(value)
    except ValueError:
        return False
    canonical = str(parsed)
    if canonical != value.lower():
        return False
    return canonical in UUID_EXTREMES or parsed.version in UUID_VERSIONS


def read_session_id(cookies: Mapping[str, str], config: SessionCookieConfig) -> str | None:
    raw = cookies.get(config.name)
    if raw is None:
        return None
    value = read_signed(raw, config.secrets)
    return value if value is not None and _is_session_id(value) else None


def _attributes(config: SessionCookieConfig) -> str:
    secure = "; Secure" if config.production else ""
    return f"HttpOnly{secure}; SameSite={COOKIE_SAME_SITE.capitalize()}"


def set_cookie_header(session_id: str, config: SessionCookieConfig, max_age_seconds: int, expires_at: datetime) -> str:
    value = quote(f"{SIGNED_COOKIE_PREFIX}{sign(session_id, config.secrets[0])}", safe="")
    expires = format_datetime(expires_at, usegmt=True)
    lifetime = f"Max-Age={max_age_seconds}; Path={COOKIE_PATH}; Expires={expires}"
    return f"{config.name}={value}; {lifetime}; {_attributes(config)}"


def clear_cookie_header(config: SessionCookieConfig) -> str:
    return f"{config.name}=; Path={COOKIE_PATH}; Expires={EPOCH_EXPIRES}; {_attributes(config)}"
