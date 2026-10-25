from typing import TYPE_CHECKING

from starlette.datastructures import Headers

from app.constants.http import FORWARDED_FOR_HEADER, UNKNOWN_CLIENT

if TYPE_CHECKING:
    from starlette.types import Scope

FORWARDED_SEPARATOR = ","


def client_ip(scope: Scope, *, trust_proxy: bool) -> str:
    if trust_proxy:
        forwarded = Headers(scope=scope).get(FORWARDED_FOR_HEADER)
        first = forwarded.split(FORWARDED_SEPARATOR)[0].strip() if forwarded else ""
        if first:
            return first
    client = scope.get("client")
    return str(client[0]) if client else UNKNOWN_CLIENT
