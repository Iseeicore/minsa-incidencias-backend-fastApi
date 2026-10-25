import base64
from datetime import UTC, datetime

import pytest

from app.incidencias.domain.cursores import (
    PosicionDeDerivacion,
    PosicionDeListado,
    PosicionPorVencer,
    codificar_cursor,
    codificar_cursor_de_derivacion,
    codificar_cursor_por_vencer,
    decodificar_cursor,
    decodificar_cursor_de_derivacion,
    decodificar_cursor_por_vencer,
)

ID = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"
INSTANTE = datetime(2026, 10, 24, 12, 0, 0, 123_000, tzinfo=UTC)
FECHA = "2026-10-24T12:00:00.123Z"


def _cursor(texto: str) -> str:
    return base64.urlsafe_b64encode(texto.encode()).decode().rstrip("=")


def test_el_cursor_del_listado_es_base64url_de_fecha_y_id_como_en_el_node() -> None:
    assert codificar_cursor(PosicionDeListado(INSTANTE, ID)) == _cursor(f"{FECHA}|{ID}")


def test_el_cursor_del_listado_va_y_vuelve() -> None:
    posicion = PosicionDeListado(INSTANTE, ID)

    assert decodificar_cursor(codificar_cursor(posicion)) == posicion


def test_el_cursor_trunca_los_microsegundos_a_milisegundos_como_el_node() -> None:
    con_micros = datetime(2026, 10, 24, 12, 0, 0, 123_456, tzinfo=UTC)

    assert decodificar_cursor(codificar_cursor(PosicionDeListado(con_micros, ID))) == PosicionDeListado(INSTANTE, ID)


def test_el_cursor_del_listado_acepta_el_id_en_mayusculas() -> None:
    posicion = decodificar_cursor(_cursor(f"{FECHA}|{ID.upper()}"))

    assert posicion is not None
    assert posicion.id == ID.upper()


@pytest.mark.parametrize(
    "texto",
    [
        f"2026-10-24T12:00:00Z|{ID}",
        f"2026-10-24T12:00:00.123+00:00|{ID}",
        f"2026-10-24 12:00:00.123Z|{ID}",
        f"2026-13-24T12:00:00.123Z|{ID}",
        f"no-es-fecha|{ID}",
        f"{FECHA}|no-es-uuid",
        f"{FECHA}|{ID.replace('-', '')}",
        f"{FECHA}",
        f"{FECHA}|{ID}|sobra",
        "",
    ],
)
def test_un_cursor_de_listado_con_forma_invalida_se_rechaza(texto: str) -> None:
    assert decodificar_cursor(_cursor(texto) if texto else "") is None


def test_un_cursor_que_no_es_base64url_se_rechaza() -> None:
    assert decodificar_cursor("###") is None
    assert decodificar_cursor_por_vencer("###") is None


def test_el_cursor_por_vencer_lleva_marca_y_va_y_vuelve() -> None:
    posicion = PosicionPorVencer(INSTANTE, ID)
    cursor = codificar_cursor_por_vencer(posicion)

    assert cursor == _cursor(f"por-vencer|vence-en|{FECHA}|{ID}")
    assert decodificar_cursor_por_vencer(cursor) == posicion


@pytest.mark.parametrize(
    "texto",
    [
        f"listado|vence-en|{FECHA}|{ID}",
        f"por-vencer|otra|{FECHA}|{ID}",
        f"por-vencer|vence-en|{FECHA}",
        f"por-vencer|vence-en|2026|{ID}",
        f"por-vencer|vence-en|{FECHA}|no-es-uuid",
        f"{FECHA}|{ID}",
    ],
)
def test_un_cursor_por_vencer_con_forma_invalida_se_rechaza(texto: str) -> None:
    assert decodificar_cursor_por_vencer(_cursor(texto)) is None


def test_un_cursor_de_un_tipo_no_sirve_para_el_otro() -> None:
    assert decodificar_cursor(codificar_cursor_por_vencer(PosicionPorVencer(INSTANTE, ID))) is None
    assert decodificar_cursor_por_vencer(codificar_cursor(PosicionDeListado(INSTANTE, ID))) is None


def test_el_cursor_de_derivaciones_es_base64url_de_marca_fecha_e_id_como_en_el_node() -> None:
    assert codificar_cursor_de_derivacion(PosicionDeDerivacion(INSTANTE, "4821")) == _cursor(
        f"derivaciones|{FECHA}|4821"
    )


def test_el_cursor_de_derivaciones_va_y_vuelve_y_trunca_a_milisegundos() -> None:
    con_micros = datetime(2026, 10, 24, 12, 0, 0, 123_456, tzinfo=UTC)

    posicion = decodificar_cursor_de_derivacion(codificar_cursor_de_derivacion(PosicionDeDerivacion(con_micros, "7")))

    assert posicion == PosicionDeDerivacion(INSTANTE, "7")


def test_el_cursor_de_derivaciones_acepta_el_identificador_mas_grande_de_bigint() -> None:
    posicion = decodificar_cursor_de_derivacion(_cursor(f"derivaciones|{FECHA}|9223372036854775807"))

    assert posicion == PosicionDeDerivacion(INSTANTE, "9223372036854775807")


@pytest.mark.parametrize(
    "texto",
    [
        f"derivaciones|{FECHA}|9223372036854775808",
        f"derivaciones|{FECHA}|12345678901234567890",
        f"derivaciones|{FECHA}|0",
        f"derivaciones|{FECHA}|04821",
        f"derivaciones|{FECHA}|-5",
        f"derivaciones|{FECHA}|4.5",
        f"derivaciones|{FECHA}|١٢٣",
        f"derivaciones|{FECHA}|",
        "derivaciones|2026-10-24T12:00:00Z|4821",
        "derivaciones|2026-10-24T12:00:00.123+00:00|4821",
        "derivaciones|no-es-fecha|4821",
        f"otra|{FECHA}|4821",
        f"derivaciones|{FECHA}",
        f"derivaciones|{FECHA}|4821|sobra",
        f"{FECHA}|4821",
        "",
    ],
)
def test_un_cursor_de_derivaciones_con_forma_invalida_se_rechaza(texto: str) -> None:
    assert decodificar_cursor_de_derivacion(_cursor(texto)) is None


def test_un_texto_que_no_es_base64url_no_es_un_cursor_de_derivaciones() -> None:
    assert decodificar_cursor_de_derivacion("###") is None


def test_el_cursor_de_derivaciones_no_sirve_para_el_listado() -> None:
    assert decodificar_cursor(codificar_cursor_de_derivacion(PosicionDeDerivacion(INSTANTE, "4821"))) is None
