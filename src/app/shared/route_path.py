from typing import TYPE_CHECKING

from app.constants.sesion import LOGOUT_METHOD, LOGOUT_PATH

if TYPE_CHECKING:
    from starlette.types import Scope


def route_path(scope: Scope) -> str:
    path: str = scope["path"]
    root: str = scope.get("root_path", "")
    return path.removeprefix(root) if root and path.startswith(root) else path


def is_logout(scope: Scope) -> bool:
    return scope["method"] == LOGOUT_METHOD and route_path(scope) == LOGOUT_PATH
