import pytest

from app.errors.datos_invalidos import DatosInvalidos
from app.incidencias.domain.descripcion_de_derivacion import descripcion_de_derivacion, descripcion_si_se_envia

MENSAJE = "Describe el motivo de la derivación con entre 10 y 2000 caracteres."


def test_la_descripcion_se_devuelve_sin_espacios_en_los_extremos() -> None:
    assert descripcion_de_derivacion("  Motivo suficiente  ") == "Motivo suficiente"


@pytest.mark.parametrize("texto", ["", "corto", " " * 20, "x" * 9, "x" * 2001])
def test_una_descripcion_fuera_de_10_a_2000_caracteres_se_rechaza(texto: str) -> None:
    with pytest.raises(DatosInvalidos, match=MENSAJE):
        descripcion_de_derivacion(texto)


def test_los_limites_de_longitud_se_aceptan() -> None:
    assert len(descripcion_de_derivacion("x" * 10)) == 10
    assert len(descripcion_de_derivacion("x" * 2000)) == 2000


def test_una_descripcion_ausente_no_se_valida_cuando_es_opcional() -> None:
    assert descripcion_si_se_envia(None) is None


def test_una_descripcion_enviada_se_valida_aunque_sea_opcional() -> None:
    assert descripcion_si_se_envia("  Motivo suficiente ") == "Motivo suficiente"
    with pytest.raises(DatosInvalidos, match=MENSAJE):
        descripcion_si_se_envia("corto")
