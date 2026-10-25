from app.constants.lexico_corrupcion import CLASES_DE_LEXICO


def _por_palabra() -> dict[str, tuple[str, ...]]:
    por_palabra: dict[str, list[str]] = {}
    for nombre, palabras in CLASES_DE_LEXICO.items():
        for palabra in palabras:
            por_palabra.setdefault(palabra, []).append(nombre)
    return {palabra: tuple(nombres) for palabra, nombres in por_palabra.items()}


CLASES = CLASES_DE_LEXICO
CLASES_POR_PALABRA = _por_palabra()
