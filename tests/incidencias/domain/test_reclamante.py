import pytest

from app.incidencias.domain.reclamante import describir_reclamante


def test_un_reclamante_anonimo_se_muestra_como_anonimo_aunque_haya_datos() -> None:
    assert describir_reclamante(es_anonimo=True, nombre="Luis Quispe", dni="12345678") == "Anónimo"


@pytest.mark.parametrize(
    ("nombre", "dni", "esperado"),
    [
        ("Luis Alberto Quispe", "12345678", "Luis A. · DNI ••••5678"),
        ("  luis   alberto ", None, "luis A."),
        ("Luis", "12345678", "Luis · DNI ••••5678"),
        ("Luis A", "9999", "Luis A · DNI ••••"),
        ("Luis ñandú", None, "Luis Ñ."),
        (None, "12345678", "DNI ••••5678"),
        (None, "123", "DNI ••••"),
        ("", "  ", "Sin datos"),
        (None, None, "Sin datos"),
        ("   ", None, "Sin datos"),
    ],
)
def test_un_reclamante_con_datos_se_abrevia_y_enmascara_el_documento(
    nombre: str | None, dni: str | None, esperado: str
) -> None:
    assert describir_reclamante(es_anonimo=False, nombre=nombre, dni=dni) == esperado
