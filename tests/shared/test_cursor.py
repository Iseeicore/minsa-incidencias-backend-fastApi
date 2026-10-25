import base64

import pytest

from app.shared.cursor import (
    PosicionPorNombre,
    decode_int_cursor,
    decode_parts,
    decode_uuid_cursor,
    encode_int_cursor,
    encode_parts,
    encode_uuid_cursor,
)

UUID_MINUSCULAS = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"
PG_INT_MAX = 2_147_483_647


def _cursor(texto: str) -> str:
    return base64.urlsafe_b64encode(texto.encode()).decode().rstrip("=")


def test_las_partes_se_codifican_y_se_leen_sin_relleno() -> None:
    cursor = encode_parts(["a", "b|c"])

    assert "=" not in cursor
    assert decode_parts(cursor) == ["a", "b", "c"]


def test_el_cursor_de_uuid_va_y_vuelve_con_acentos_y_barras_en_el_nombre() -> None:
    posicion = PosicionPorNombre("Ñandú | Pérez", UUID_MINUSCULAS)

    assert decode_uuid_cursor(encode_uuid_cursor(posicion)) == posicion


def test_el_cursor_de_entero_va_y_vuelve() -> None:
    posicion = PosicionPorNombre("Hospital Uno", 42)

    assert decode_int_cursor(encode_int_cursor(posicion)) == posicion


def test_el_cursor_coincide_con_el_formato_base64url_del_node() -> None:
    assert encode_uuid_cursor(PosicionPorNombre("Ana", UUID_MINUSCULAS)) == _cursor(f"{UUID_MINUSCULAS}|Ana")


@pytest.mark.parametrize(
    "cursor",
    ["", "no es base64!", "abc+def/", _cursor("sin-separador"), _cursor(f"{UUID_MINUSCULAS}|")],
    ids=["vacio", "alfabeto", "estandar", "sin-separador", "nombre-vacio"],
)
def test_un_cursor_mal_formado_de_uuid_se_rechaza(cursor: str) -> None:
    assert decode_uuid_cursor(cursor) is None


@pytest.mark.parametrize(
    "texto",
    [
        f"{UUID_MINUSCULAS.upper()}|Ana",
        f"{UUID_MINUSCULAS.replace('-', '')}|Ana",
        f"no-es-uuid|Ana",  # noqa: F541
        f"{UUID_MINUSCULAS}|{'x' * 301}",
        f"{UUID_MINUSCULAS}|con\u0000nul",
    ],
    ids=["mayusculas", "sin-guiones", "no-uuid", "nombre-largo", "nul"],
)
def test_un_cursor_de_uuid_con_contenido_invalido_se_rechaza(texto: str) -> None:
    assert decode_uuid_cursor(_cursor(texto)) is None


def test_un_nombre_de_300_caracteres_es_valido() -> None:
    nombre = "x" * 300

    assert decode_uuid_cursor(_cursor(f"{UUID_MINUSCULAS}|{nombre}")) == PosicionPorNombre(nombre, UUID_MINUSCULAS)


@pytest.mark.parametrize(
    "texto", ["0|Ana", "01|Ana", "-1|Ana", "1.5|Ana", "x|Ana", "12345678901|Ana", f"{PG_INT_MAX + 1}|Ana"]
)
def test_un_cursor_de_entero_con_identificador_invalido_se_rechaza(texto: str) -> None:
    assert decode_int_cursor(_cursor(texto)) is None


def test_el_mayor_entero_de_postgres_es_valido() -> None:
    assert decode_int_cursor(_cursor(f"{PG_INT_MAX}|Ana")) == PosicionPorNombre("Ana", PG_INT_MAX)


def test_un_cursor_que_no_es_utf8_se_rechaza() -> None:
    invalido = base64.urlsafe_b64encode(b"\xff\xfe|Ana").decode().rstrip("=")

    assert decode_parts(invalido) is None
