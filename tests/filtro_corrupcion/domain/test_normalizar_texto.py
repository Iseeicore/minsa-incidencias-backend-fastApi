import pytest

from app.filtro_corrupcion.domain.normalizar_texto import (
    es_numero,
    marcar_montos,
    normalizar_texto,
    palabra_normalizada,
    tokenizar,
)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Hola Mundo", "hola mundo"),
        ("ÑANDÚ, PÉREZ!", "nandu perez"),
        ("  varios   espacios  ", "varios espacios"),
        ("S/. 50", "s 50"),
        ("¡¿Qué?! 123", "que 123"),
        ("a-b_c", "a b c"),
        ("", ""),
        ("!!!", ""),
        ("é", "e"),
        ("a !́ b", "a b"),
        ("ß", "ß"),
        ("😀 ok", "ok"),
        ("١٢٣", "١٢٣"),
    ],
)
def test_normalizar_baja_a_minusculas_quita_marcas_y_deja_palabras_separadas_por_un_espacio(
    texto: str, esperado: str
) -> None:
    assert normalizar_texto(texto) == esperado


def test_la_palabra_normalizada_da_lo_mismo_que_normalizar() -> None:
    assert palabra_normalizada("Cirugía") == normalizar_texto("Cirugía") == "cirugia"


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("Me pidió plata", ["me", "pidio", "plata"]), ("", []), ("   ", []), ("¡¡!!", []), ("uno", ["uno"])],
)
def test_tokenizar_separa_el_texto_normalizado_en_palabras(texto: str, esperado: list[str]) -> None:
    assert tokenizar(texto) == esperado


@pytest.mark.parametrize(
    ("palabra", "esperado"),
    [("123", True), ("0", True), ("12a", False), ("", False), (None, False), ("١٢٣", False), ("1.5", False)],
)
def test_solo_los_digitos_ascii_son_un_numero(palabra: str | None, esperado: bool) -> None:  # noqa: FBT001
    assert es_numero(palabra) is esperado


@pytest.mark.parametrize(
    ("palabras", "esperado"),
    [
        (["pidio", "100", "soles", "para"], ["pidio", "monto", "para"]),
        (["pidio", "s", "50", "ya"], ["pidio", "monto", "ya"]),
        (["pidio", "50", "dolares"], ["pidio", "monto"]),
        (["costo", "50", "sol"], ["costo", "monto"]),
        (["tiene", "30", "anos"], ["tiene", "anos"]),
        (["el", "50"], ["el"]),
        (["s", "tiene", "razon"], ["s", "tiene", "razon"]),
        (["soles", "de", "plata"], ["soles", "de", "plata"]),
        ([], []),
    ],
)
def test_marcar_montos_reemplaza_la_cifra_de_dinero_y_quita_el_resto_de_numeros(
    palabras: list[str], esperado: list[str]
) -> None:
    assert marcar_montos(palabras) == esperado
