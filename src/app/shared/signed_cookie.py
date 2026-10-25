import base64
import hashlib
import hmac
from typing import TYPE_CHECKING
from urllib.parse import unquote

from app.constants.sesion import SIGNED_COOKIE_PREFIX

if TYPE_CHECKING:
    from collections.abc import Sequence

SIGNATURE_SEPARATOR = "."
BASE64_PADDING = "="


def sign(value: str, secret: str) -> str:
    mac = hmac.new(secret.encode(), value.encode(), hashlib.sha256).digest()
    return f"{value}{SIGNATURE_SEPARATOR}{base64.b64encode(mac).decode().rstrip(BASE64_PADDING)}"


def unsign(signed: str, secret: str) -> str | None:
    separator = signed.rfind(SIGNATURE_SEPARATOR)
    if separator < 0:
        return None
    value = signed[:separator]
    return value if hmac.compare_digest(sign(value, secret).encode(), signed.encode()) else None


def read_signed(raw: str, secrets: Sequence[str]) -> str | None:
    decoded = unquote(raw)
    if not decoded.startswith(SIGNED_COOKIE_PREFIX):
        return None
    signed = decoded.removeprefix(SIGNED_COOKIE_PREFIX)
    for secret in secrets:
        value = unsign(signed, secret)
        if value is not None:
            return value
    return None
