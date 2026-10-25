from dataclasses import dataclass
from functools import cache, lru_cache, partial
from typing import TYPE_CHECKING

from app.constants.filtro_corrupcion import (
    FAMILIA_DE_COBRO,
    MARCA_DE_HUECO,
    PALABRAS_DE_CARGO_SUELTAS,
    PESO_POR_TIPO,
    PUNTOS_UBICACION,
    VERBOS_DE_COBRO_ADICIONALES,
)
from app.constants.lexico_corrupcion import (
    CARGOS,
    FRASES_DE_ACOSO,
    FRASES_DE_PRUEBAS,
    FRASES_DEBILES,
    FRASES_DEBILES_DE_COBRO,
    FRASES_FUERTES,
    FRASES_FUERTES_DE_COBRO,
    FRASES_MEDIAS,
    FRASES_MEDIAS_DE_COBRO,
    FRASES_NEGATIVAS_DECISIVAS,
    FRASES_NEGATIVAS_LEVES,
    PALABRAS_QUE_ENGANAN,
    PLANTILLAS_DE_LA_FAMILIA_DE_COBRO,
)
from app.enums.tipo_senal import TipoSenal
from app.filtro_corrupcion.domain.catalogo import ubicaciones_de_entidades
from app.filtro_corrupcion.domain.clases_lexico import CLASES
from app.filtro_corrupcion.domain.coincidencias import (
    EntradaPonderada,
    ItemCompilado,
    compilar_plantilla,
    crear_indice,
)
from app.filtro_corrupcion.domain.normalizar_texto import tokenizar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from app.enums.nivel_cargo import NivelCargo
    from app.filtro_corrupcion.domain.coincidencias import Indice, Patron
    from app.filtro_corrupcion.domain.tipos import EntidadCatalogo, UbicacionEntidad


@dataclass(frozen=True, slots=True, kw_only=True)
class EntradaDeSenal(EntradaPonderada):
    tipo: TipoSenal
    negable: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class EntradaDeCargo(EntradaPonderada):
    nivel: NivelCargo


@dataclass(frozen=True, slots=True, kw_only=True)
class EntradaDeEntidad(EntradaPonderada):
    entidad: EntidadCatalogo


@dataclass(frozen=True, slots=True, kw_only=True)
class EntradaDeUbicacion(EntradaPonderada):
    ubicacion: UbicacionEntidad


@dataclass(frozen=True, slots=True)
class IndiceDeEntidades:
    entradas: list[ItemCompilado[EntradaDeEntidad]]
    indice: Indice[EntradaDeEntidad]


def _es_palabra_que_engana(patron: Patron) -> bool:
    return len(patron) == 1 and patron[0] in PALABRAS_QUE_ENGANAN


def _compilar[T: EntradaPonderada](plantillas: Iterable[str], entrada_de: Callable[[str], T]) -> list[ItemCompilado[T]]:
    items: list[ItemCompilado[T]] = []
    for plantilla in plantillas:
        entrada = entrada_de(plantilla)
        items.extend(
            ItemCompilado(patron, entrada)
            for patron in compilar_plantilla(plantilla)
            if not _es_palabra_que_engana(patron)
        )
    return items


def _entradas_de_senal(plantillas: Iterable[str], tipo: TipoSenal) -> list[ItemCompilado[EntradaDeSenal]]:
    return _compilar(
        plantillas,
        lambda grupo: EntradaDeSenal(
            tipo=tipo,
            peso=PESO_POR_TIPO[tipo],
            grupo=grupo,
            negable=False,
            familia=FAMILIA_DE_COBRO if grupo in PLANTILLAS_DE_LA_FAMILIA_DE_COBRO else None,
        ),
    )


def _entradas_generalizadas(plantillas: Iterable[str], tipo: TipoSenal) -> list[ItemCompilado[EntradaDeSenal]]:
    return _compilar(
        plantillas,
        lambda grupo: EntradaDeSenal(
            tipo=tipo, peso=PESO_POR_TIPO[tipo], grupo=grupo, negable=True, familia=FAMILIA_DE_COBRO
        ),
    )


@cache
def indice_de_senales() -> Indice[EntradaDeSenal]:
    return crear_indice(
        [
            *_entradas_de_senal(FRASES_FUERTES, TipoSenal.FUERTE),
            *_entradas_de_senal(FRASES_MEDIAS, TipoSenal.MEDIA),
            *_entradas_de_senal(FRASES_DEBILES, TipoSenal.DEBIL),
            *_entradas_generalizadas(FRASES_FUERTES_DE_COBRO, TipoSenal.FUERTE),
            *_entradas_generalizadas(FRASES_MEDIAS_DE_COBRO, TipoSenal.MEDIA),
            *_entradas_generalizadas(FRASES_DEBILES_DE_COBRO, TipoSenal.DEBIL),
            *_entradas_de_senal(FRASES_NEGATIVAS_DECISIVAS, TipoSenal.NEGATIVA_DECISIVA),
            *_entradas_de_senal(FRASES_NEGATIVAS_LEVES, TipoSenal.NEGATIVA_LEVE),
        ]
    )


@cache
def indice_de_acoso() -> Indice[EntradaPonderada]:
    return crear_indice(_compilar(FRASES_DE_ACOSO, lambda grupo: EntradaPonderada(peso=0, grupo=grupo)))


@cache
def indice_de_pruebas() -> Indice[EntradaPonderada]:
    return crear_indice(_compilar(FRASES_DE_PRUEBAS, lambda grupo: EntradaPonderada(peso=0, grupo=grupo)))


def _entrada_de_cargo(nivel: NivelCargo, grupo: str) -> EntradaDeCargo:
    return EntradaDeCargo(nivel=nivel, peso=PESO_POR_TIPO[TipoSenal.ACTOR], grupo=grupo)


@cache
def entradas_de_cargo() -> list[ItemCompilado[EntradaDeCargo]]:
    items: list[ItemCompilado[EntradaDeCargo]] = []
    for plantilla, nivel in CARGOS:
        items.extend(_compilar([plantilla], partial(_entrada_de_cargo, nivel)))
    return items


@cache
def indice_de_cargos() -> Indice[EntradaDeCargo]:
    return crear_indice(entradas_de_cargo())


@cache
def palabras_de_cargo() -> frozenset[str]:
    palabras = {palabra for item in entradas_de_cargo() for palabra in item.patron if palabra != MARCA_DE_HUECO}
    return frozenset(palabras | PALABRAS_DE_CARGO_SUELTAS)


@cache
def verbos_de_cobro() -> frozenset[str]:
    return frozenset({*CLASES.get("verbo_cobro", frozenset()), *VERBOS_DE_COBRO_ADICIONALES})


@cache
def indice_de_ubicaciones() -> Indice[EntradaDeUbicacion]:
    return crear_indice(
        [
            ItemCompilado(
                tuple(tokenizar(ubicacion.zona)),
                EntradaDeUbicacion(ubicacion=ubicacion, peso=PUNTOS_UBICACION, grupo=ubicacion.zona),
            )
            for ubicacion in ubicaciones_de_entidades()
        ]
    )


@lru_cache(maxsize=32)
def indice_de_entidades(entidades: tuple[EntidadCatalogo, ...]) -> IndiceDeEntidades:
    entradas = [
        ItemCompilado(
            tuple(patron),
            EntradaDeEntidad(entidad=entidad, peso=PESO_POR_TIPO[TipoSenal.ENTIDAD], grupo=entidad.codigo),
        )
        for entidad in entidades
        for texto in (entidad.nombre, *entidad.alias, *entidad.alias_derivados)
        if (patron := tokenizar(texto))
    ]
    return IndiceDeEntidades(entradas, crear_indice(entradas))
