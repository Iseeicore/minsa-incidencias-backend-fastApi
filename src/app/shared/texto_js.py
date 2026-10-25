BLANCOS_DE_JS = frozenset(
    "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029\u202f\u205f\u3000\ufeff"
)
CARACTERES_DE_BLANCO_DE_JS = "".join(sorted(BLANCOS_DE_JS))


def recortar_como_js(texto: str) -> str:
    return texto.strip(CARACTERES_DE_BLANCO_DE_JS)


def longitud_como_js(texto: str) -> int:
    return len(texto.encode("utf-16-le")) // 2


def separar_por_blancos_de_js(texto: str) -> list[str]:
    piezas: list[str] = []
    actual: list[str] = []
    for caracter in texto:
        if caracter in BLANCOS_DE_JS:
            if actual:
                piezas.append("".join(actual))
                actual = []
        else:
            actual.append(caracter)
    if actual:
        piezas.append("".join(actual))
    return piezas
