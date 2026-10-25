def codigo_renipress_buscado(texto: str) -> str | None:
    limpio = texto.strip()
    if not (limpio.isascii() and limpio.isdigit()):
        return None
    return limpio.lstrip("0") or "0"
