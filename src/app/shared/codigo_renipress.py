from app.constants.renipress import CODIGO_RENIPRESS_LONGITUD_MAXIMA


def codigo_renipress_canonico(texto: str) -> str | None:
    canonico = texto.strip().lstrip("0")
    es_numero = canonico.isascii() and canonico.isdigit()
    return canonico if es_numero and len(canonico) <= CODIGO_RENIPRESS_LONGITUD_MAXIMA else None


def codigo_renipress_buscado(texto: str) -> str | None:
    limpio = texto.strip()
    if not (limpio.isascii() and limpio.isdigit()):
        return None
    return limpio.lstrip("0") or "0"
