import pytest

from app.shared.text_search import escape_wildcards, like_pattern


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("ana", "ana"),
        ("100%", "100\\%"),
        ("a_b", "a\\_b"),
        ("a\\b", "a\\\\b"),
        ("%_\\", "\\%\\_\\\\"),
    ],
)
def test_escapa_los_comodines_de_like(texto: str, esperado: str) -> None:
    assert escape_wildcards(texto) == esperado


def test_el_patron_envuelve_el_texto_escapado() -> None:
    assert like_pattern("a%") == "%a\\%%"


@pytest.mark.parametrize("texto", [None, ""])
def test_sin_texto_no_hay_patron(texto: str | None) -> None:
    assert like_pattern(texto) is None
