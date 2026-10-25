from urllib.parse import unquote, urlsplit

from app.constants.database import SUFIJOS_DE_BASE_DESECHABLE
from app.errors.base_no_desechable import BaseNoDesechable


def asegurar_base_desechable(url: str) -> None:
    nombre = unquote(urlsplit(url).path.removeprefix("/"))
    if not nombre.endswith(SUFIJOS_DE_BASE_DESECHABLE):
        raise BaseNoDesechable
