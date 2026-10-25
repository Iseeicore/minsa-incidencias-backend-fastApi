from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants.filtro_corrupcion import (
    PALABRAS_DE_APELLIDO_DEL_NOMBRE,
    PALABRAS_MINIMAS_NOMBRE_PROPIO,
    PALABRAS_SEGUIDAS_PARA_NOMBRE,
    PARTICULAS_DE_NOMBRE,
    TITULOS_ESTANDAR_DEL_CARGO_MAXIMO,
)
from app.enums.nivel_cargo import NivelCargo
from app.enums.tipo_senal import TipoSenal
from app.filtro_corrupcion.domain.coincidencias import buscar_coincidencias
from app.filtro_corrupcion.domain.deteccion_de_senales import texto_de
from app.filtro_corrupcion.domain.lexico import (
    indice_de_entidades,
    indice_de_ubicaciones,
    palabras_de_cargo,
)
from app.filtro_corrupcion.domain.nombres_propios import nombres_propios_de
from app.filtro_corrupcion.domain.normalizar_texto import normalizar_texto, tokenizar
from app.filtro_corrupcion.domain.tipos import (
    EntidadDetectada,
    ReferenciaDerivacion,
    SenalDetectada,
    TitularDetectado,
    UbicacionDetectada,
)
from app.shared.texto_js import separar_por_blancos_de_js

if TYPE_CHECKING:
    from app.filtro_corrupcion.domain.coincidencias import Coincidencia
    from app.filtro_corrupcion.domain.lexico import EntradaDeEntidad, IndiceDeEntidades
    from app.filtro_corrupcion.domain.tipos import ActorDetectado, EntidadCatalogo


@dataclass(frozen=True, slots=True)
class EntidadHallada:
    entidad: EntidadDetectada
    catalogo: EntidadCatalogo
    senal: SenalDetectada


@dataclass(frozen=True, slots=True)
class TitularNombrado:
    catalogo: EntidadCatalogo
    frase: str


@dataclass(frozen=True, slots=True)
class UbicacionHallada:
    ubicacion: UbicacionDetectada
    senal: SenalDetectada


def entidad_detectada_de(catalogo: EntidadCatalogo) -> EntidadDetectada:
    return EntidadDetectada(catalogo.codigo, catalogo.nombre, catalogo.tipo)


def _es_ambigua(coincidencia: Coincidencia[EntradaDeEntidad], palabras: list[str], indice: IndiceDeEntidades) -> bool:
    if coincidencia.fin >= len(palabras):
        return False
    siguiente = palabras[coincidencia.fin]
    largo = len(coincidencia.patron)
    return any(
        item.entrada.entidad.codigo != coincidencia.entrada.entidad.codigo
        and len(item.patron) > largo
        and item.patron[largo] == siguiente
        and item.patron[:largo] == coincidencia.patron
        for item in indice.entradas
    )


def detectar_entidad(palabras: list[str], entidades: tuple[EntidadCatalogo, ...]) -> EntidadHallada | None:
    indice = indice_de_entidades(entidades)
    candidatas = sorted(
        (c for c in buscar_coincidencias(palabras, indice.indice) if not _es_ambigua(c, palabras, indice)),
        key=lambda c: (c.inicio, -c.fin),
    )
    if not candidatas:
        return None
    mejor = candidatas[0]
    catalogo = mejor.entrada.entidad
    senal = SenalDetectada(texto_de(palabras, mejor), TipoSenal.ENTIDAD, mejor.entrada.peso)
    return EntidadHallada(entidad_detectada_de(catalogo), catalogo, senal)


def _identifica_al_titular(distintas: list[str], apellidos: set[str]) -> bool:
    return len(distintas) >= PALABRAS_SEGUIDAS_PARA_NOMBRE and (
        len(distintas) > PALABRAS_DE_APELLIDO_DEL_NOMBRE or any(palabra in apellidos for palabra in distintas)
    )


def palabras_del_nombre_del_titular(palabras: list[str], nombre_titular: str | None) -> list[str] | None:
    if not nombre_titular:
        return None
    propias = [palabra for palabra in tokenizar(nombre_titular) if palabra not in PARTICULAS_DE_NOMBRE]
    conocidas = set(propias)
    apellidos = set(propias[-PALABRAS_DE_APELLIDO_DEL_NOMBRE:])
    mejor: list[str] | None = None
    racha: list[str] = []

    def cerrar() -> None:
        nonlocal mejor, racha
        distintas = list(dict.fromkeys(racha))
        if _identifica_al_titular(distintas, apellidos) and len(distintas) > len(mejor or []):
            mejor = racha
        racha = []

    for palabra in palabras:
        if palabra in conocidas:
            racha.append(palabra)
        elif not (racha and palabra in PARTICULAS_DE_NOMBRE):
            cerrar()
    cerrar()
    return mejor


def detectar_titular_nombrado(
    palabras: list[str], entidades: tuple[EntidadCatalogo, ...], detectada: EntidadCatalogo | None
) -> TitularNombrado | None:
    candidatas: list[tuple[EntidadCatalogo, list[str], int]] = []
    for catalogo in (detectada,) if detectada is not None else entidades:
        nombre = catalogo.titular.nombre if catalogo.titular is not None else None
        coincidencia = palabras_del_nombre_del_titular(palabras, nombre)
        if coincidencia is not None:
            candidatas.append((catalogo, coincidencia, len(set(coincidencia))))
    maximo = max([0, *(distintas for _, _, distintas in candidatas)])
    mejores = [candidata for candidata in candidatas if candidata[2] == maximo]
    if len(mejores) != 1:
        return None
    catalogo, coincidencia, _ = mejores[0]
    return TitularNombrado(catalogo, " ".join(coincidencia))


def detectar_ubicacion(
    palabras: list[str], entidades: tuple[EntidadCatalogo, ...], *, establecimiento_conocido: bool
) -> UbicacionHallada | None:
    codigos = {entidad.codigo for entidad in entidades}
    candidatas = sorted(
        (
            c
            for c in buscar_coincidencias(palabras, indice_de_ubicaciones())
            if c.entrada.ubicacion.codigo_entidad in codigos
            and not (establecimiento_conocido and c.entrada.ubicacion.ambigua_con_establecimiento)
        ),
        key=lambda c: (c.inicio, -c.fin),
    )
    if not candidatas:
        return None
    mejor = candidatas[0]
    ubicacion = mejor.entrada.ubicacion
    return UbicacionHallada(
        UbicacionDetectada(ubicacion.zona, ubicacion.codigo_entidad),
        SenalDetectada(texto_de(palabras, mejor), TipoSenal.UBICACION, mejor.entrada.peso),
    )


def detectar_titular(actor: ActorDetectado | None, *, nombre_coincide: bool) -> TitularDetectado | None:
    if actor is None or actor.nivel != NivelCargo.CARGO_MAXIMO:
        return None
    return TitularDetectado(actor.cargo, actor.cargo not in TITULOS_ESTANDAR_DEL_CARGO_MAXIMO, nombre_coincide)


def titular_por_su_nombre(catalogo: EntidadCatalogo) -> TitularDetectado | None:
    if catalogo.titular is None or not catalogo.titular.cargo:
        return None
    titulo = normalizar_texto(catalogo.titular.cargo)
    es_estandar = any(titulo.startswith(estandar) for estandar in TITULOS_ESTANDAR_DEL_CARGO_MAXIMO)
    return TitularDetectado(catalogo.titular.cargo, not es_estandar, nombre_coincide=True)


def referencia_de(catalogo: EntidadCatalogo, titular: TitularDetectado | None) -> ReferenciaDerivacion:
    destino = catalogo.destino_si_titular
    return ReferenciaDerivacion(
        codigo_entidad=catalogo.codigo,
        contactos_disponibles=catalogo.contactos_disponibles,
        destino_si_titular=destino,
        aplica_al_titular=destino is not None and titular is not None,
    )


def detectar_nombre_mencionado(texto: str) -> str | None:
    cargos = palabras_de_cargo()
    for candidato in nombres_propios_de(texto):
        palabras = separar_por_blancos_de_js(candidato)
        while palabras and " ".join(tokenizar(palabras[0])) in cargos:
            palabras.pop(0)
        if len(palabras) >= PALABRAS_MINIMAS_NOMBRE_PROPIO:
            return " ".join(palabras)
    return None
