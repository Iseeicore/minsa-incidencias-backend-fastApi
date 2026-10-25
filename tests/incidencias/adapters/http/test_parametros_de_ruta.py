import pytest

from app.errors.no_encontrado import NoEncontrado
from app.incidencias.adapters.http.parametros_de_ruta import (
    codigo_de_incidencia,
    identificador_de_evidencia,
    renipress_de_ruta,
)

UUID = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"


@pytest.mark.parametrize("codigo", ["MINSA-2026-000001", "MINSA-1999-123456", "MINSA-2026-1234567890"])
def test_un_codigo_con_el_formato_minsa_aaaa_nnnnnn_pasa(codigo: str) -> None:
    assert codigo_de_incidencia(codigo) == codigo


@pytest.mark.parametrize(
    "codigo",
    [
        "",
        "conteos",
        "MINSA-2026-00001",
        "MINSA-26-000001",
        "MINSA-20267-000001",
        "minsa-2026-000001",
        "OTRO-2026-000001",
        "MINSA-2026-00000a",
        "MINSA-2026-000001-1",
        "MINSA-2026",
        "MINSA-\u0662\u0660\u0662\u0666-\u0660\u0660\u0660\u0660\u0660\u0661",
    ],
)
def test_un_codigo_con_otro_formato_es_404_con_el_mensaje_general(codigo: str) -> None:
    with pytest.raises(NoEncontrado) as capturado:
        codigo_de_incidencia(codigo)

    assert capturado.value.message == "El recurso solicitado no existe."


def test_una_evidencia_con_uuid_en_minusculas_pasa() -> None:
    assert identificador_de_evidencia(UUID) == UUID


@pytest.mark.parametrize("identificador", ["", "x", UUID.upper(), UUID.replace("-", ""), f"{{{UUID}}}"])
def test_una_evidencia_que_no_es_uuid_en_minusculas_es_404_con_su_mensaje(identificador: str) -> None:
    with pytest.raises(NoEncontrado) as capturado:
        identificador_de_evidencia(identificador)

    assert capturado.value.message == "La evidencia solicitada no existe."


@pytest.mark.parametrize(
    ("texto", "canonico"), [("1234", "1234"), ("00001234", "1234"), ("  7 ", "7"), ("12345678", "12345678")]
)
def test_un_codigo_renipress_se_devuelve_sin_ceros_a_la_izquierda(texto: str, canonico: str) -> None:
    assert renipress_de_ruta(texto) == canonico


@pytest.mark.parametrize("texto", ["", "0", "abc", "12a", "123456789", "-1", "١٢"])
def test_un_codigo_renipress_invalido_es_404_con_el_mensaje_del_establecimiento(texto: str) -> None:
    with pytest.raises(NoEncontrado) as capturado:
        renipress_de_ruta(texto)

    assert capturado.value.message == "El establecimiento no está disponible."
