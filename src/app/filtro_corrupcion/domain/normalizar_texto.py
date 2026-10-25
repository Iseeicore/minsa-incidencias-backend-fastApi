import unicodedata
from functools import cache

from app.constants.filtro_corrupcion import PALABRA_DE_MONTO, PALABRAS_DE_UN_MONTO

ESPACIO = " "
CATEGORIA_DE_MARCA = "M"
CATEGORIAS_DE_PALABRA = "LN"


def normalizar_texto(texto: str) -> str:
    piezas: list[str] = []
    for caracter in unicodedata.normalize("NFD", texto.lower()):
        categoria = unicodedata.category(caracter)[0]
        if categoria == CATEGORIA_DE_MARCA:
            continue
        if categoria in CATEGORIAS_DE_PALABRA:
            piezas.append(caracter)
        elif piezas and piezas[-1] != ESPACIO:
            piezas.append(ESPACIO)
    return "".join(piezas).strip(ESPACIO)


@cache
def palabra_normalizada(palabra: str) -> str:
    return normalizar_texto(palabra)


def tokenizar(texto: str) -> list[str]:
    normalizado = normalizar_texto(texto)
    return normalizado.split(ESPACIO) if normalizado else []


def es_numero(palabra: str | None) -> bool:
    return palabra is not None and palabra.isascii() and palabra.isdigit()


def _palabra_en(posicion: int, palabras: list[str]) -> str | None:
    return palabras[posicion] if 0 <= posicion < len(palabras) else None


def marcar_montos(palabras: list[str]) -> list[str]:
    resultado: list[str] = []
    for indice, palabra in enumerate(palabras):
        anterior = _palabra_en(indice - 1, palabras)
        siguiente = _palabra_en(indice + 1, palabras)
        if es_numero(palabra):
            es_dinero = (siguiente is not None and siguiente in PALABRAS_DE_UN_MONTO) or anterior == "s"
            if es_dinero:
                resultado.append(PALABRA_DE_MONTO)
            continue
        if palabra in PALABRAS_DE_UN_MONTO and es_numero(anterior):
            continue
        if palabra == "s" and es_numero(siguiente):
            continue
        resultado.append(palabra)
    return resultado
