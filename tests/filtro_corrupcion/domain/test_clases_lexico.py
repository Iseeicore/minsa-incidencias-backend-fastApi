from app.filtro_corrupcion.domain.clases_lexico import CLASES, CLASES_POR_PALABRA
from app.filtro_corrupcion.domain.normalizar_texto import normalizar_texto

NOMBRES_DE_CLASES = {
    "verbo_cobro",
    "verbo_cobrar",
    "complemento",
    "bien_vendible",
    "tercero",
    "bien_publico_fuerte",
    "bien_publico_ambiguo",
    "pariente",
    "pariente_directo",
    "conocidos",
    "negocio",
    "verbo_colocar",
    "accion_favor",
    "cola_o_lista",
}


def test_las_catorce_clases_del_lexico_existen() -> None:
    assert set(CLASES) == NOMBRES_DE_CLASES


def test_las_palabras_de_las_clases_ya_estan_normalizadas() -> None:
    assert all(normalizar_texto(palabra) == palabra for palabras in CLASES.values() for palabra in palabras)


def test_cada_palabra_sabe_a_que_clases_pertenece_en_el_orden_del_lexico() -> None:
    assert CLASES_POR_PALABRA["cobran"] == ("verbo_cobro", "verbo_cobrar")
    assert CLASES_POR_PALABRA["cola"] == ("cola_o_lista",)
    assert "bien_vendible" in CLASES_POR_PALABRA["cita"]


def test_una_palabra_fuera_de_todas_las_clases_no_aparece() -> None:
    assert "zapato" not in CLASES_POR_PALABRA
