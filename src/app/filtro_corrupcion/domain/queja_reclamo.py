from dataclasses import dataclass
from functools import cache

from app.constants.filtro_queja_reclamo import (
    DISTANCIA_NEGACION_CON_PRONOMBRE,
    FRASES_DE_QUEJA,
    FRASES_DE_RECLAMO,
    PALABRAS_QUE_NIEGAN_QUEJA_RECLAMO,
    PRONOMBRES_ENTRE_NEGACION_Y_VERBO,
)
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.filtro_corrupcion.domain.normalizar_texto import tokenizar
from app.filtro_corrupcion.domain.tipos import ResultadoQuejaReclamo, SenalQuejaReclamo

SIN_PALABRA = ""


@dataclass(frozen=True, slots=True, eq=False)
class EntradaDeLexico:
    palabras: tuple[str, ...]
    categoria: CategoriaIncidencia


@dataclass(frozen=True, slots=True, eq=False)
class CoincidenciaDeFrase:
    entrada: EntradaDeLexico
    inicio: int
    fin: int


def _entradas_de(frases: tuple[str, ...], categoria: CategoriaIncidencia) -> tuple[EntradaDeLexico, ...]:
    return tuple(EntradaDeLexico(tuple(tokenizar(frase)), categoria) for frase in frases)


@cache
def lexico_de_quejas_y_reclamos() -> tuple[EntradaDeLexico, ...]:
    return (
        *_entradas_de(FRASES_DE_RECLAMO, CategoriaIncidencia.RECLAMO),
        *_entradas_de(FRASES_DE_QUEJA, CategoriaIncidencia.QUEJA),
    )


@cache
def _negadores() -> frozenset[str]:
    return frozenset(palabra for frase in PALABRAS_QUE_NIEGAN_QUEJA_RECLAMO for palabra in tokenizar(frase))


def _palabra_en(palabras: list[str], posicion: int) -> str:
    return palabras[posicion] if 0 <= posicion < len(palabras) else SIN_PALABRA


def _esta_negada(inicio: int, palabras: list[str]) -> bool:
    anterior = _palabra_en(palabras, inicio - 1)
    if anterior in _negadores():
        return True
    return anterior in PRONOMBRES_ENTRE_NEGACION_Y_VERBO and (
        _palabra_en(palabras, inicio - DISTANCIA_NEGACION_CON_PRONOMBRE) in _negadores()
    )


def _posiciones_por_palabra(palabras: list[str]) -> dict[str, list[int]]:
    posiciones: dict[str, list[int]] = {}
    for posicion, palabra in enumerate(palabras):
        posiciones.setdefault(palabra, []).append(posicion)
    return posiciones


def _coincidencias_de(
    entrada: EntradaDeLexico, palabras: list[str], posiciones: dict[str, list[int]]
) -> list[CoincidenciaDeFrase]:
    largo = len(entrada.palabras)
    return [
        CoincidenciaDeFrase(entrada, inicio, inicio + largo)
        for inicio in posiciones.get(entrada.palabras[0], ())
        if tuple(palabras[inicio : inicio + largo]) == entrada.palabras and not _esta_negada(inicio, palabras)
    ]


def _contiene_a(externa: CoincidenciaDeFrase, interna: CoincidenciaDeFrase) -> bool:
    return (
        externa is not interna
        and externa.inicio <= interna.inicio
        and interna.fin <= externa.fin
        and externa.fin - externa.inicio > interna.fin - interna.inicio
    )


def _senales_sin_repetir(coincidencias: list[CoincidenciaDeFrase]) -> tuple[SenalQuejaReclamo, ...]:
    conservadas = [c for c in coincidencias if not any(_contiene_a(otra, c) for otra in coincidencias)]
    conservadas.sort(key=lambda coincidencia: coincidencia.inicio)
    frases: dict[str, SenalQuejaReclamo] = {}
    for coincidencia in conservadas:
        frase = " ".join(coincidencia.entrada.palabras)
        frases.setdefault(frase, SenalQuejaReclamo(frase, coincidencia.entrada.categoria))
    return tuple(frases.values())


def _categoria_de(senales: tuple[SenalQuejaReclamo, ...]) -> CategoriaIncidencia | None:
    categorias = {senal.categoria for senal in senales}
    if CategoriaIncidencia.RECLAMO in categorias:
        return CategoriaIncidencia.RECLAMO
    return CategoriaIncidencia.QUEJA if CategoriaIncidencia.QUEJA in categorias else None


def evaluar_texto_queja_reclamo(texto: str) -> ResultadoQuejaReclamo:
    palabras = tokenizar(texto)
    posiciones = _posiciones_por_palabra(palabras)
    coincidencias = [
        coincidencia
        for entrada in lexico_de_quejas_y_reclamos()
        for coincidencia in _coincidencias_de(entrada, palabras, posiciones)
    ]
    senales = _senales_sin_repetir(coincidencias)
    return ResultadoQuejaReclamo(_categoria_de(senales), senales)
