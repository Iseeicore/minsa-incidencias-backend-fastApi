import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants.filtro_corrupcion import (
    BANDA_COINCIDEN_DEBIL,
    BANDA_COINCIDEN_FUERTE,
    BANDA_DISCREPAN,
    BANDA_SOLO_UNO,
    FACTOR_DOS_DECIMALES,
    FUENTES_PARA_ACUERDO,
    PESO_IA_DESCARTA_CORRUPCION,
    PESO_IA_FUERTE,
    PESO_IA_VE_CORRUPCION,
    PESO_MAXIMO_IA,
    POSICION_DE_DISCREPANCIA,
    RECORRIDO_DESCARTE_IA,
    RECORRIDO_DESCARTE_REGLAS,
    RECORRIDO_FUERZA_REGLAS,
    TOPE_CONFIANZA,
    UMBRAL_CERTEZA_MEDIA,
    UMBRAL_TOTAL_CORRUPCION,
)
from app.enums.acuerdo_reglas_ia import AcuerdoReglasIa
from app.enums.certeza_corrupcion import CertezaCorrupcion
from app.filtro_corrupcion.domain.tipos import ResultadoCombinacion

if TYPE_CHECKING:
    from app.filtro_corrupcion.domain.tipos import ResultadoCorrupcion

type Banda = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Confianza:
    acuerdo: AcuerdoReglasIa
    confianza: float


def redondear_como_js(valor: float) -> int:
    return math.floor(valor + 0.5)


def acotar(valor: float, minimo: float = 0, maximo: float = 1) -> float:
    return min(maximo, max(minimo, valor))


def normalizar_peso_ia(peso: float | None) -> int | None:
    if peso is None or math.isnan(peso):
        return None
    return int(acotar(redondear_como_js(peso), 0, PESO_MAXIMO_IA))


def dentro_de_la_banda(banda: Banda, posicion: float) -> float:
    minimo, maximo = banda
    valor = minimo + acotar(posicion) * (maximo - minimo)
    return redondear_como_js(min(valor, TOPE_CONFIANZA) * FACTOR_DOS_DECIMALES) / FACTOR_DOS_DECIMALES


def _fuerza_de_reglas_que_ven(puntaje: int) -> float:
    return acotar((puntaje - UMBRAL_CERTEZA_MEDIA) / RECORRIDO_FUERZA_REGLAS)


def _descarte_de_reglas(puntaje: int) -> float:
    return acotar((UMBRAL_CERTEZA_MEDIA - 1 - puntaje) / RECORRIDO_DESCARTE_REGLAS)


def _confianza_sin_modelo(reglas: ResultadoCorrupcion) -> Confianza:
    if reglas.propuesta_corrupcion:
        posicion = _fuerza_de_reglas_que_ven(reglas.puntaje)
    elif reglas.requiere_segunda_opinion:
        posicion = 0
    else:
        posicion = _descarte_de_reglas(reglas.puntaje)
    return Confianza(AcuerdoReglasIa.SIN_MODELO, dentro_de_la_banda(BANDA_SOLO_UNO, posicion))


def _coinciden_en_ver(reglas: ResultadoCorrupcion, peso_ia: int) -> Confianza:
    fuerte = reglas.certeza == CertezaCorrupcion.ALTA and peso_ia >= PESO_IA_FUERTE
    posicion = (
        _fuerza_de_reglas_que_ven(reglas.puntaje)
        + (peso_ia - PESO_IA_VE_CORRUPCION) / (PESO_MAXIMO_IA - PESO_IA_VE_CORRUPCION)
    ) / FUENTES_PARA_ACUERDO
    banda = BANDA_COINCIDEN_FUERTE if fuerte else BANDA_COINCIDEN_DEBIL
    return Confianza(AcuerdoReglasIa.COINCIDEN, dentro_de_la_banda(banda, posicion))


def _coinciden_en_descartar(reglas: ResultadoCorrupcion, peso_ia: int) -> Confianza:
    reglas_descartan = not reglas.propuesta_corrupcion and reglas.puntaje <= 0
    fuerte = reglas_descartan and peso_ia <= PESO_IA_DESCARTA_CORRUPCION
    posicion = (
        _descarte_de_reglas(reglas.puntaje)
        + acotar((PESO_IA_DESCARTA_CORRUPCION + 1 - peso_ia) / RECORRIDO_DESCARTE_IA)
    ) / FUENTES_PARA_ACUERDO
    banda = BANDA_COINCIDEN_FUERTE if fuerte else BANDA_COINCIDEN_DEBIL
    return Confianza(AcuerdoReglasIa.COINCIDEN, dentro_de_la_banda(banda, posicion))


def _confianza_por_acuerdo(reglas: ResultadoCorrupcion, peso_ia: int, *, propuesta_final: bool) -> Confianza:
    reglas_ven = reglas.propuesta_corrupcion
    ia_ve = peso_ia >= PESO_IA_VE_CORRUPCION
    ia_descarta = peso_ia <= PESO_IA_DESCARTA_CORRUPCION
    reglas_descartan = not reglas_ven and reglas.puntaje <= 0
    if reglas_ven and ia_ve:
        return _coinciden_en_ver(reglas, peso_ia)
    if not reglas_ven and not ia_ve:
        if propuesta_final:
            return Confianza(AcuerdoReglasIa.SOLO_UNO, dentro_de_la_banda(BANDA_SOLO_UNO, 0))
        return _coinciden_en_descartar(reglas, peso_ia)
    if (reglas_ven and ia_descarta) or (not reglas_ven and ia_ve and reglas_descartan):
        return Confianza(AcuerdoReglasIa.DISCREPAN, dentro_de_la_banda(BANDA_DISCREPAN, POSICION_DE_DISCREPANCIA))
    posicion = (
        _fuerza_de_reglas_que_ven(reglas.puntaje)
        if reglas_ven
        else (peso_ia - PESO_IA_VE_CORRUPCION) / (PESO_MAXIMO_IA - PESO_IA_VE_CORRUPCION)
    )
    return Confianza(AcuerdoReglasIa.SOLO_UNO, dentro_de_la_banda(BANDA_SOLO_UNO, posicion))


def combinar_reglas_con_ia(reglas: ResultadoCorrupcion, peso_ia: float | None) -> ResultadoCombinacion:
    peso = normalizar_peso_ia(peso_ia)
    puntaje_total = reglas.puntaje + (peso or 0)
    subida_por_ia = not reglas.propuesta_corrupcion and peso is not None and puntaje_total > UMBRAL_TOTAL_CORRUPCION
    propuesta_corrupcion = reglas.propuesta_corrupcion or subida_por_ia
    confianza = (
        _confianza_sin_modelo(reglas)
        if peso is None
        else _confianza_por_acuerdo(reglas, peso, propuesta_final=propuesta_corrupcion)
    )
    duda_sin_modelo = reglas.requiere_segunda_opinion and peso is None
    revision_otrans = propuesta_corrupcion or duda_sin_modelo
    return ResultadoCombinacion(
        propuesta_corrupcion=propuesta_corrupcion,
        puntaje_reglas=reglas.puntaje,
        peso_ia=peso,
        puntaje_total=puntaje_total,
        umbral=UMBRAL_TOTAL_CORRUPCION,
        subida_por_ia=subida_por_ia,
        acuerdo=confianza.acuerdo,
        confianza=confianza.confianza,
        requiere_otrans=propuesta_corrupcion,
        revision_otrans=revision_otrans,
        requiere_revision_humana=revision_otrans or confianza.acuerdo == AcuerdoReglasIa.DISCREPAN,
    )
