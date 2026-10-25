import pytest

from app.shared.texto_js import longitud_como_js, recortar_como_js, separar_por_blancos_de_js


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("  hola  ", "hola"),
        ("\t\n hola \r\n", "hola"),
        ("\ufeff\u00a0hola\u00a0\ufeff", "hola"),
        ("\u2003hola\u3000", "hola"),
        ("\u0085hola\u0085", "\u0085hola\u0085"),
        ("a b", "a b"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_el_recorte_quita_los_mismos_blancos_que_trim_de_javascript(texto: str, esperado: str) -> None:
    assert recortar_como_js(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("", 0), ("hola", 4), ("ñandú", 5), ("😀", 2), ("a😀b", 4), ("é", 1), ("é", 2)],
)
def test_la_longitud_cuenta_unidades_utf16_como_length_de_javascript(texto: str, esperado: int) -> None:
    assert longitud_como_js(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("a b  c", ["a", "b", "c"]),
        ("  a b  ", ["a", "b"]),
        ("a\u00a0b\u2028c", ["a", "b", "c"]),
        ("\u0085a", ["\u0085a"]),
        ("", []),
        ("   ", []),
        ("sola", ["sola"]),
    ],
)
def test_separar_por_blancos_ignora_los_vacios_y_usa_los_blancos_de_javascript(texto: str, esperado: list[str]) -> None:
    assert separar_por_blancos_de_js(texto) == esperado
