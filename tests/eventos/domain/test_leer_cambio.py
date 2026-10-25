import json

import pytest

from app.errors.alcance_de_incidencia_invalido import AlcanceDeIncidenciaInvalido
from app.eventos.domain.cambio_de_incidencia import CambioDeIncidencia
from app.eventos.domain.leer_cambio import leer_cambio

COMPLETO = {"areaAntes": None, "areaDespues": 10, "categoriaAntes": None, "categoriaDespues": 3}


def test_un_aviso_vacio_no_trae_alcance() -> None:
    assert leer_cambio(None) is None
    assert leer_cambio("") is None


def test_un_aviso_completo_se_lee_con_sus_cuatro_identificadores() -> None:
    assert leer_cambio(json.dumps(COMPLETO)) == CambioDeIncidencia(None, 10, None, 3)


def test_los_campos_de_mas_se_ignoran() -> None:
    assert leer_cambio(json.dumps({**COMPLETO, "extra": "x"})) == CambioDeIncidencia(None, 10, None, 3)


@pytest.mark.parametrize(
    "payload",
    [
        "null",
        "[]",
        "5",
        json.dumps({"areaAntes": None}),
        json.dumps({**COMPLETO, "areaDespues": 0}),
        json.dumps({**COMPLETO, "areaDespues": -3}),
        json.dumps({**COMPLETO, "categoriaDespues": "3"}),
        json.dumps({**COMPLETO, "categoriaDespues": 1.5}),
        json.dumps({**COMPLETO, "categoriaDespues": True}),
        json.dumps({**COMPLETO, "areaAntes": 2**53}),
    ],
)
def test_un_aviso_sin_alcance_valido_se_rechaza(payload: str) -> None:
    with pytest.raises(AlcanceDeIncidenciaInvalido):
        leer_cambio(payload)


def test_un_texto_que_no_es_json_se_rechaza_como_error_de_valor() -> None:
    with pytest.raises(ValueError, match="Expecting"):
        leer_cambio("{no es json")
