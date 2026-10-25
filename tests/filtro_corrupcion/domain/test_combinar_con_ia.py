import math

import pytest

from app.enums.acuerdo_reglas_ia import AcuerdoReglasIa
from app.enums.certeza_corrupcion import CertezaCorrupcion
from app.filtro_corrupcion.domain.combinar_con_ia import (
    acotar,
    combinar_reglas_con_ia,
    dentro_de_la_banda,
    normalizar_peso_ia,
    redondear_como_js,
)
from tests.helpers.corrupcion import un_resultado_de_corrupcion


@pytest.mark.parametrize(
    ("valor", "esperado"), [(2.5, 3), (-2.5, -2), (0.49, 0), (0.5, 1), (4.5, 5), (-0.5, 0), (7.0, 7), (-3.7, -4)]
)
def test_el_redondeo_es_el_de_math_round_de_javascript(valor: float, esperado: int) -> None:
    assert redondear_como_js(valor) == esperado


@pytest.mark.parametrize(
    ("peso", "esperado"),
    [(None, None), (math.nan, None), (6, 6), (6.4, 6), (4.5, 5), (11, 10), (-3, 0), (0.49, 0), (10.4, 10)],
)
def test_el_peso_de_la_ia_se_redondea_y_se_acota_de_0_a_10(peso: float | None, esperado: int | None) -> None:
    assert normalizar_peso_ia(peso) == esperado


def test_acotar_deja_el_valor_dentro_del_rango() -> None:
    assert (acotar(-1), acotar(0.4), acotar(7), acotar(5, 0, 10), acotar(-5, 0, 10)) == (0, 0.4, 1, 5, 0)


@pytest.mark.parametrize(
    ("banda", "posicion", "esperado"),
    [((45, 65), 0, 45.0), ((45, 65), 1, 65.0), ((80, 95), 0.5, 87.5), ((45, 65), 1 / 3, 51.67), ((80, 95), 2, 95.0)],
)
def test_la_confianza_se_ubica_dentro_de_su_banda_con_dos_decimales(
    banda: tuple[int, int], posicion: float, esperado: float
) -> None:
    assert dentro_de_la_banda(banda, posicion) == esperado


def test_sin_modelo_y_con_propuesta_de_las_reglas_la_confianza_crece_con_el_puntaje() -> None:
    reglas = un_resultado_de_corrupcion(puntaje=4, propuesta_corrupcion=True, certeza=CertezaCorrupcion.ALTA)

    combinacion = combinar_reglas_con_ia(reglas, None)

    assert (combinacion.acuerdo, combinacion.confianza, combinacion.peso_ia) == (AcuerdoReglasIa.SIN_MODELO, 53.0, None)
    assert (combinacion.requiere_otrans, combinacion.revision_otrans, combinacion.subida_por_ia) == (True, True, False)
    assert (combinacion.puntaje_total, combinacion.umbral) == (4, 5)


def test_sin_modelo_y_con_duda_de_las_reglas_pide_revision_aunque_no_proponga() -> None:
    reglas = un_resultado_de_corrupcion(puntaje=1, requiere_segunda_opinion=True)

    combinacion = combinar_reglas_con_ia(reglas, None)

    assert (combinacion.confianza, combinacion.propuesta_corrupcion) == (45.0, False)
    assert (combinacion.revision_otrans, combinacion.requiere_revision_humana) == (True, True)


def test_sin_modelo_y_sin_nada_que_ver_descarta_con_confianza_baja() -> None:
    combinacion = combinar_reglas_con_ia(un_resultado_de_corrupcion(puntaje=0), None)

    assert (combinacion.confianza, combinacion.revision_otrans, combinacion.requiere_revision_humana) == (
        51.67,
        False,
        False,
    )


def test_cuando_reglas_e_ia_ven_corrupcion_coinciden_con_banda_fuerte_si_la_certeza_es_alta() -> None:
    reglas = un_resultado_de_corrupcion(puntaje=6, propuesta_corrupcion=True, certeza=CertezaCorrupcion.ALTA)

    fuerte = combinar_reglas_con_ia(reglas, 8)
    debil = combinar_reglas_con_ia(un_resultado_de_corrupcion(puntaje=3, propuesta_corrupcion=True), 5)

    assert (fuerte.acuerdo, fuerte.confianza, fuerte.puntaje_total) == (AcuerdoReglasIa.COINCIDEN, 90.5, 14)
    assert (debil.acuerdo, debil.confianza) == (AcuerdoReglasIa.COINCIDEN, 65 + 0.1 * 15)


def test_cuando_las_reglas_ven_y_la_ia_descarta_discrepan_y_se_pide_revision() -> None:
    reglas = un_resultado_de_corrupcion(puntaje=4, propuesta_corrupcion=True)

    combinacion = combinar_reglas_con_ia(reglas, 1)

    assert (combinacion.acuerdo, combinacion.confianza) == (AcuerdoReglasIa.DISCREPAN, 40.0)
    assert combinacion.requiere_revision_humana is True


def test_si_la_ia_sube_el_total_por_encima_del_umbral_se_propone_aunque_las_reglas_no() -> None:
    reglas = un_resultado_de_corrupcion(puntaje=1)

    combinacion = combinar_reglas_con_ia(reglas, 5)

    assert (combinacion.subida_por_ia, combinacion.propuesta_corrupcion, combinacion.puntaje_total) == (True, True, 6)
    assert (combinacion.acuerdo, combinacion.confianza) == (AcuerdoReglasIa.SOLO_UNO, 45.0)


def test_si_las_reglas_descartan_del_todo_y_la_ia_ve_discrepan() -> None:
    combinacion = combinar_reglas_con_ia(un_resultado_de_corrupcion(puntaje=0), 6)

    assert (combinacion.acuerdo, combinacion.subida_por_ia) == (AcuerdoReglasIa.DISCREPAN, True)


def test_si_ninguno_ve_corrupcion_coinciden_en_descartar_y_la_banda_es_fuerte_solo_si_ambos_descartan() -> None:
    fuerte = combinar_reglas_con_ia(un_resultado_de_corrupcion(puntaje=0), 1)
    debil = combinar_reglas_con_ia(un_resultado_de_corrupcion(puntaje=1), 4)

    assert (fuerte.acuerdo, fuerte.confianza) == (AcuerdoReglasIa.COINCIDEN, 87.5)
    assert (debil.acuerdo, debil.requiere_otrans) == (AcuerdoReglasIa.COINCIDEN, False)
    assert debil.confianza < 80


def test_si_solo_las_reglas_ven_con_ia_dudosa_queda_en_solo_uno() -> None:
    reglas = un_resultado_de_corrupcion(puntaje=4, propuesta_corrupcion=True)

    combinacion = combinar_reglas_con_ia(reglas, 3)

    assert (combinacion.acuerdo, combinacion.confianza) == (AcuerdoReglasIa.SOLO_UNO, 53.0)


def test_el_peso_nulo_equivale_a_no_haber_tenido_modelo() -> None:
    reglas = un_resultado_de_corrupcion(puntaje=2)

    assert combinar_reglas_con_ia(reglas, None).acuerdo == AcuerdoReglasIa.SIN_MODELO
    assert combinar_reglas_con_ia(reglas, math.nan).peso_ia is None


def test_si_el_total_supera_el_umbral_sin_que_la_ia_vea_corrupcion_queda_en_solo_uno_con_confianza_minima() -> None:
    combinacion = combinar_reglas_con_ia(un_resultado_de_corrupcion(puntaje=4), 4)

    assert combinacion.subida_por_ia is True
    assert (combinacion.acuerdo, combinacion.confianza) == (AcuerdoReglasIa.SOLO_UNO, 45.0)
