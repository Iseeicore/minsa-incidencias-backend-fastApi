import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.filtro_corrupcion.domain.queja_reclamo import evaluar_texto_queja_reclamo, lexico_de_quejas_y_reclamos
from app.filtro_corrupcion.domain.tipos import SenalQuejaReclamo

QUEJA = CategoriaIncidencia.QUEJA
RECLAMO = CategoriaIncidencia.RECLAMO


def _frases(texto: str) -> list[str]:
    return [senal.frase for senal in evaluar_texto_queja_reclamo(texto).senales]


def test_el_lexico_pone_primero_los_reclamos_y_normaliza_cada_frase() -> None:
    lexico = lexico_de_quejas_y_reclamos()

    assert len(lexico) == 132
    assert (lexico[0].palabras, lexico[0].categoria) == (("cobro",), RECLAMO)
    assert (lexico[-1].palabras, lexico[-1].categoria) == (("suciedad",), QUEJA)
    assert ("historia", "clinica") in {entrada.palabras for entrada in lexico}


def test_un_texto_vacio_o_sin_frases_del_lexico_no_tiene_categoria() -> None:
    assert evaluar_texto_queja_reclamo("").categoria is None
    assert evaluar_texto_queja_reclamo("buenos dias a todos").senales == ()


def test_las_senales_salen_en_el_orden_del_texto_con_su_categoria() -> None:
    resultado = evaluar_texto_queja_reclamo("Me cobraron en la boleta y fue grosero")

    assert resultado.senales == (
        SenalQuejaReclamo("cobraron", RECLAMO),
        SenalQuejaReclamo("boleta", RECLAMO),
        SenalQuejaReclamo("grosero", QUEJA),
    )


def test_el_reclamo_gana_cuando_hay_reclamo_y_queja() -> None:
    assert evaluar_texto_queja_reclamo("grosero y me cobraron").categoria == RECLAMO
    assert evaluar_texto_queja_reclamo("fue muy grosero").categoria == QUEJA


def test_las_tildes_y_mayusculas_no_impiden_encontrar_la_frase() -> None:
    assert _frases("DEVOLUCIÓN de mi dinero") == ["devolucion"]
    assert _frases("Historia Clínica extraviada") == ["historia clinica"]


@pytest.mark.parametrize(
    "texto",
    ["no cobraron nada", "nunca me cobraron", "tampoco nos cobran", "nadie te cobro", "ni boleta ni nada"],
)
def test_una_negacion_justo_antes_apaga_la_frase(texto: str) -> None:
    assert evaluar_texto_queja_reclamo(texto).senales == ()


def test_el_pronombre_deja_pasar_la_negacion_solo_una_palabra() -> None:
    assert _frases("no me cobraron") == []
    assert _frases("no sabia que me cobraron") == ["cobraron"]


def test_al_principio_del_texto_no_se_mira_hacia_atras() -> None:
    assert _frases("cobraron todo") == ["cobraron"]
    assert _frases("me cobraron no") == ["cobraron"]
    assert _frases("me cobraron no nada") == ["cobraron"]


def test_la_frase_larga_absorbe_a_la_corta_que_contiene() -> None:
    assert _frases("me trato mal en la cita") == ["me trato mal", "cita"]


def test_una_frase_repetida_se_informa_una_sola_vez() -> None:
    assert _frases("cobro, otro cobro y mas cobro") == ["cobro"]


def test_dos_frases_de_igual_largo_que_se_cruzan_se_conservan() -> None:
    assert _frases("no me explicaron nada") == ["no me explicaron"]
