import unicodedata

from app.shared.texto_js import BLANCOS_DE_JS

MAYUSCULA = "Lu"
MINUSCULA = "Ll"


def _fin_de_palabra_propia(texto: str, inicio: int) -> int | None:
    if inicio >= len(texto) or unicodedata.category(texto[inicio]) != MAYUSCULA:
        return None
    fin = inicio + 1
    while fin < len(texto) and unicodedata.category(texto[fin]) == MINUSCULA:
        fin += 1
    return fin if fin > inicio + 1 else None


def _fin_de_blancos(texto: str, inicio: int) -> int:
    fin = inicio
    while fin < len(texto) and texto[fin] in BLANCOS_DE_JS:
        fin += 1
    return fin


def _nombre_en(texto: str, inicio: int) -> int | None:
    fin = _fin_de_palabra_propia(texto, inicio)
    if fin is None:
        return None
    palabras = 1
    while True:
        siguiente = _fin_de_blancos(texto, fin)
        if siguiente == fin:
            break
        fin_siguiente = _fin_de_palabra_propia(texto, siguiente)
        if fin_siguiente is None:
            break
        fin = fin_siguiente
        palabras += 1
    return fin if palabras > 1 else None


def nombres_propios_de(texto: str) -> list[str]:
    nombres: list[str] = []
    posicion = 0
    while posicion < len(texto):
        fin = _nombre_en(texto, posicion)
        if fin is None:
            posicion += 1
        else:
            nombres.append(texto[posicion:fin])
            posicion = fin
    return nombres
