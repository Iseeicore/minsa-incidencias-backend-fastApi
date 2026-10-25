from datetime import date

import pytest

from app.incidencias.domain.rango_fechas import dia_de, dias_del_rango


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("2026-03-10", date(2026, 3, 10)), ("2024-02-29", date(2024, 2, 29)), ("0001-01-01", date(1, 1, 1))],
)
def test_un_dia_real_con_el_formato_aaaa_mm_dd_se_lee(texto: str, esperado: date) -> None:
    assert dia_de(texto) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "",
        "2026-3-10",
        "2026-03-1",
        "26-03-10",
        "2026/03/10",
        "2026-02-30",
        "2025-02-29",
        "2026-13-01",
        "2026-00-10",
        "abcd-ef-gh",
        "2026-03-10 ",
        "\u0662\u0660\u0662\u0666-\u0660\u0663-\u0661\u0660",
    ],
)
def test_lo_que_no_es_un_dia_real_con_ese_formato_no_se_lee(texto: str) -> None:
    assert dia_de(texto) is None


@pytest.mark.parametrize(
    ("desde", "hasta", "dias"),
    [
        ("2026-03-10", "2026-03-10", 1),
        ("2026-03-10", "2026-03-11", 2),
        ("2026-03-11", "2026-03-10", 0),
        ("2026-03-12", "2026-03-10", -1),
        ("2026-01-01", "2026-12-31", 365),
        ("2024-01-01", "2024-12-31", 366),
    ],
)
def test_los_dias_del_rango_cuentan_ambos_extremos(desde: str, hasta: str, dias: int) -> None:
    assert dias_del_rango(desde, hasta) == dias


def test_un_rango_con_un_extremo_invalido_no_tiene_dias() -> None:
    assert dias_del_rango("2026-02-30", "2026-03-10") is None
    assert dias_del_rango("2026-03-10", "basura") is None
