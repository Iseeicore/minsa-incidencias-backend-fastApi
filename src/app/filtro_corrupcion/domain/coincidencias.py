from dataclasses import dataclass
from functools import cache

from app.constants.filtro_corrupcion import HUECO_MAXIMO_PALABRAS, MARCA_DE_HUECO, PALABRA_DE_MONTO, PREFIJO_DE_CLASE
from app.errors.clase_de_lexico_desconocida import ClaseDeLexicoDesconocida
from app.filtro_corrupcion.domain.clases_lexico import CLASES, CLASES_POR_PALABRA
from app.filtro_corrupcion.domain.normalizar_texto import palabra_normalizada
from app.shared.texto_js import separar_por_blancos_de_js

type Patron = tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class EntradaPonderada:
    peso: int
    grupo: str
    familia: str | None = None


@dataclass(frozen=True, slots=True)
class ItemCompilado[T: EntradaPonderada]:
    patron: Patron
    entrada: T


@dataclass(frozen=True, slots=True)
class Coincidencia[T: EntradaPonderada]:
    entrada: T
    patron: Patron
    inicio: int
    fin: int


@dataclass(slots=True)
class GrupoDeCandidatos[T: EntradaPonderada]:
    por_segundo: dict[str, list[tuple[int, ItemCompilado[T]]]]
    generales: list[tuple[int, ItemCompilado[T]]]


type Indice[T: EntradaPonderada] = dict[str, GrupoDeCandidatos[T]]


def _grupo_entre_llaves(plantilla: str) -> tuple[str, str] | None:
    inicio = plantilla.find("{")
    while inicio != -1:
        fin = plantilla.find("}", inicio + 1)
        if fin == -1:
            return None
        interior = plantilla[inicio + 1 : fin]
        if "{" not in interior:
            return plantilla[inicio : fin + 1], interior
        inicio = plantilla.find("{", inicio + 1)
    return None


@cache
def expandir_plantilla(plantilla: str) -> tuple[str, ...]:
    grupo = _grupo_entre_llaves(plantilla)
    if grupo is None:
        return (plantilla,)
    coincidencia, opciones = grupo
    return tuple(
        frase
        for opcion in opciones.split("|")
        for frase in expandir_plantilla(plantilla.replace(coincidencia, opcion, 1))
    )


def es_clase(elemento: str) -> bool:
    return elemento.startswith(PREFIJO_DE_CLASE)


def _elemento_compilado(palabra: str) -> str:
    if palabra == MARCA_DE_HUECO:
        return palabra
    if not es_clase(palabra):
        return palabra_normalizada(palabra)
    if palabra[len(PREFIJO_DE_CLASE) :] not in CLASES:
        raise ClaseDeLexicoDesconocida(palabra)
    return palabra


def compilar_plantilla(plantilla: str) -> list[Patron]:
    return [
        tuple(_elemento_compilado(palabra) for palabra in separar_por_blancos_de_js(frase))
        for frase in expandir_plantilla(plantilla)
    ]


def _calza_elemento(elemento: str, palabra: str | None) -> bool:
    if palabra is None:
        return False
    if not es_clase(elemento):
        return palabra == elemento
    return palabra in CLASES.get(elemento[len(PREFIJO_DE_CLASE) :], frozenset())


def _saltar_montos(palabras: list[str], desde: int, elemento: str) -> int:
    posicion = desde
    while elemento != PALABRA_DE_MONTO and posicion < len(palabras) and palabras[posicion] == PALABRA_DE_MONTO:
        posicion += 1
    return posicion


def _calzar_desde(patron: Patron, palabras: list[str], posicion_patron: int, desde: int) -> int | None:
    if posicion_patron == len(patron):
        return desde
    if patron[posicion_patron] == MARCA_DE_HUECO:
        for hueco in range(HUECO_MAXIMO_PALABRAS + 1):
            fin = _calzar_desde(patron, palabras, posicion_patron + 1, desde + hueco)
            if fin is not None:
                return fin
        return None
    elemento = patron[posicion_patron]
    posicion = desde if posicion_patron == 0 else _saltar_montos(palabras, desde, elemento)
    palabra = palabras[posicion] if posicion < len(palabras) else None
    if not _calza_elemento(elemento, palabra):
        return None
    return _calzar_desde(patron, palabras, posicion_patron + 1, posicion + 1)


def _segundo_literal(patron: Patron) -> str | None:
    if not patron[1:]:
        return None
    segundo = patron[1]
    return None if segundo == MARCA_DE_HUECO or es_clase(segundo) else segundo


def crear_indice[T: EntradaPonderada](items: list[ItemCompilado[T]]) -> Indice[T]:
    indice: Indice[T] = {}
    for orden, item in enumerate(items):
        primera = item.patron[0] if item.patron else None
        if primera is None or primera == MARCA_DE_HUECO:
            continue
        grupo = indice.setdefault(primera, GrupoDeCandidatos({}, []))
        segundo = _segundo_literal(item.patron)
        destino = grupo.generales if segundo is None else grupo.por_segundo.setdefault(segundo, [])
        destino.append((orden, item))
    return indice


def _seleccionados[T: EntradaPonderada](
    grupo: GrupoDeCandidatos[T], directa: str | None, sin_montos: str | None
) -> list[ItemCompilado[T]]:
    if not grupo.por_segundo:
        return [item for _, item in grupo.generales]
    elegidos = list(grupo.generales)
    if directa == PALABRA_DE_MONTO:
        elegidos.extend(grupo.por_segundo.get(PALABRA_DE_MONTO, ()))
    if sin_montos is not None and sin_montos != PALABRA_DE_MONTO:
        elegidos.extend(grupo.por_segundo.get(sin_montos, ()))
    elegidos.sort(key=lambda elegido: elegido[0])
    return [item for _, item in elegidos]


def _candidatos[T: EntradaPonderada](
    palabra: str, indice: Indice[T], directa: str | None, sin_montos: str | None
) -> list[ItemCompilado[T]]:
    claves = [palabra, *(f"{PREFIJO_DE_CLASE}{clase}" for clase in CLASES_POR_PALABRA.get(palabra, ()))]
    candidatos: list[ItemCompilado[T]] = []
    for clave in claves:
        grupo = indice.get(clave)
        if grupo is not None:
            candidatos.extend(_seleccionados(grupo, directa, sin_montos))
    return candidatos


def buscar_coincidencias[T: EntradaPonderada](palabras: list[str], indice: Indice[T]) -> list[Coincidencia[T]]:
    resultado: list[Coincidencia[T]] = []
    for inicio, palabra in enumerate(palabras):
        directa = palabras[inicio + 1] if inicio + 1 < len(palabras) else None
        posicion = _saltar_montos(palabras, inicio + 1, "")
        sin_montos = palabras[posicion] if posicion < len(palabras) else None
        for item in _candidatos(palabra, indice, directa, sin_montos):
            fin = _calzar_desde(item.patron, palabras, 0, inicio)
            if fin is not None:
                resultado.append(Coincidencia(item.entrada, item.patron, inicio, fin))
    return resultado


def _literales(patron: Patron) -> frozenset[str]:
    return frozenset(palabra for palabra in patron if palabra != MARCA_DE_HUECO)


def _esta_dentro[T: EntradaPonderada](interna: Coincidencia[T], externa: Coincidencia[T]) -> bool:
    return externa.inicio <= interna.inicio and interna.fin <= externa.fin


def _chocan[T: EntradaPonderada](a: Coincidencia[T], b: Coincidencia[T]) -> bool:
    if not (a.inicio < b.fin and b.inicio < a.fin):
        return False
    if a.entrada.familia is not None and a.entrada.familia == b.entrada.familia:
        return True
    a_dentro_de_b = _esta_dentro(a, b)
    b_dentro_de_a = _esta_dentro(b, a)
    if not a_dentro_de_b and not b_dentro_de_a:
        return True
    literales_a = _literales(a.patron)
    literales_b = _literales(b.patron)
    if a_dentro_de_b and literales_a <= literales_b:
        return True
    return b_dentro_de_a and literales_b <= literales_a


def _unicas_por_grupo[T: EntradaPonderada](coincidencias: list[Coincidencia[T]]) -> list[Coincidencia[T]]:
    vistas: set[str] = set()
    unicas: list[Coincidencia[T]] = []
    for coincidencia in coincidencias:
        if coincidencia.entrada.grupo not in vistas:
            vistas.add(coincidencia.entrada.grupo)
            unicas.append(coincidencia)
    return unicas


def resolver_choques[T: EntradaPonderada](coincidencias: list[Coincidencia[T]]) -> list[Coincidencia[T]]:
    por_prioridad = sorted(
        _unicas_por_grupo(coincidencias),
        key=lambda c: (-abs(c.entrada.peso), -(c.fin - c.inicio), c.inicio),
    )
    aceptadas: list[Coincidencia[T]] = []
    for candidata in por_prioridad:
        if not any(_chocan(candidata, aceptada) for aceptada in aceptadas):
            aceptadas.append(candidata)
    return sorted(aceptadas, key=lambda c: c.inicio)
