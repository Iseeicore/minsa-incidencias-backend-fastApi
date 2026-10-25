from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants.filtro_corrupcion import VENTANA_DE_NEGACION
from app.constants.lexico_corrupcion import (
    INICIOS_QUE_YA_NIEGAN,
    NEGADORES_DE_COBRO,
    NEGADORES_DENTRO_DEL_COBRO,
    PALABRAS_DE_JEFATURA,
    PALABRAS_QUE_NIEGAN,
)
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.nivel_cargo import NivelCargo
from app.enums.senal_sensible import SenalSensible
from app.enums.tipo_senal import TipoSenal
from app.filtro_corrupcion.domain.coincidencias import Coincidencia, buscar_coincidencias, resolver_choques
from app.filtro_corrupcion.domain.lexico import (
    EntradaDeSenal,
    indice_de_acoso,
    indice_de_cargos,
    indice_de_senales,
    verbos_de_cobro,
)
from app.filtro_corrupcion.domain.tipos import ActorDetectado, SenalDetectada

if TYPE_CHECKING:
    from app.filtro_corrupcion.domain.tipos import TitularDetectado

PRIORIDAD_DE_CARGO = {NivelCargo.CARGO_MAXIMO: 0, NivelCargo.CARGO_DE_LINEA: 1, NivelCargo.PERSONAL: 2}
TIPOS_NEGATIVOS = (TipoSenal.NEGATIVA_DECISIVA, TipoSenal.NEGATIVA_LEVE)


@dataclass(frozen=True, slots=True)
class AcosoDetectado:
    senal_sensible: SenalSensible | None = None
    categoria_sugerida: CategoriaIncidencia | None = None
    escalar_a_otrans: bool = False


def texto_de(palabras: list[str], coincidencia: Coincidencia) -> str:  # type: ignore[type-arg]
    return " ".join(palabras[coincidencia.inicio : coincidencia.fin])


def esta_negada_la_frase(inicio: int, fin: int, palabras: list[str]) -> bool:
    antes = palabras[max(0, inicio - VENTANA_DE_NEGACION) : inicio]
    return any(palabra in NEGADORES_DE_COBRO for palabra in antes) or any(
        palabra in NEGADORES_DENTRO_DEL_COBRO for palabra in palabras[inicio:fin]
    )


def _es_negativa_negada(coincidencia: Coincidencia[EntradaDeSenal], palabras: list[str]) -> bool:
    if coincidencia.entrada.tipo != TipoSenal.NEGATIVA_DECISIVA or coincidencia.patron[0] in INICIOS_QUE_YA_NIEGAN:
        return False
    anterior = palabras[coincidencia.inicio - 1] if coincidencia.inicio > 0 else ""
    return anterior in PALABRAS_QUE_NIEGAN


def _vale_la_senal(coincidencia: Coincidencia[EntradaDeSenal], palabras: list[str]) -> bool:
    if _es_negativa_negada(coincidencia, palabras):
        return False
    return not (coincidencia.entrada.negable and esta_negada_la_frase(coincidencia.inicio, coincidencia.fin, palabras))


def detectar_senales(palabras: list[str]) -> list[SenalDetectada]:
    encontradas = [
        coincidencia
        for coincidencia in buscar_coincidencias(palabras, indice_de_senales())
        if _vale_la_senal(coincidencia, palabras)
    ]
    negativas_vistas: set[TipoSenal] = set()
    senales: list[SenalDetectada] = []
    for coincidencia in resolver_choques(encontradas):
        tipo = coincidencia.entrada.tipo
        if tipo in TIPOS_NEGATIVOS:
            if tipo in negativas_vistas:
                continue
            negativas_vistas.add(tipo)
        senales.append(SenalDetectada(texto_de(palabras, coincidencia), tipo, coincidencia.entrada.peso))
    return senales


def detectar_actor(palabras: list[str]) -> tuple[ActorDetectado, SenalDetectada] | None:
    coincidencias = sorted(
        resolver_choques(buscar_coincidencias(palabras, indice_de_cargos())),
        key=lambda c: (PRIORIDAD_DE_CARGO[c.entrada.nivel], c.inicio),
    )
    if not coincidencias:
        return None
    mejor = coincidencias[0]
    cargo = texto_de(palabras, mejor)
    return (
        ActorDetectado(cargo, mejor.entrada.nivel),
        SenalDetectada(cargo, TipoSenal.ACTOR, mejor.entrada.peso),
    )


def es_jefatura(palabras: list[str]) -> bool:
    return any(palabra in PALABRAS_DE_JEFATURA for palabra in palabras)


def hay_verbo_de_cobro(palabras: list[str]) -> bool:
    verbos = verbos_de_cobro()
    return any(
        palabra in verbos and not esta_negada_la_frase(indice, indice + 1, palabras)
        for indice, palabra in enumerate(palabras)
    )


def detectar_acoso(
    palabras: list[str], actor: ActorDetectado | None, titular: TitularDetectado | None
) -> AcosoDetectado:
    hay_acoso = any(
        not esta_negada_la_frase(c.inicio, c.fin, palabras) for c in buscar_coincidencias(palabras, indice_de_acoso())
    )
    if not hay_acoso:
        return AcosoDetectado()
    cargo_mayor = (
        titular is not None or (actor is not None and actor.nivel == NivelCargo.CARGO_MAXIMO) or es_jefatura(palabras)
    )
    return AcosoDetectado(SenalSensible.ACOSO, CategoriaIncidencia.RECLAMO, cargo_mayor)
