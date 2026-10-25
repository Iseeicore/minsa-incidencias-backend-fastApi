import pytest
from pydantic import ValidationError

from app.filtro_corrupcion.adapters.http.schemas import EvaluacionCorrupcionResponse, EvaluacionRequest
from app.filtro_corrupcion.application.evaluar_corrupcion import EvaluarCorrupcion, SolicitudDeEvaluacion

TEXTO = "La jefa del SIS me pidio plata para atenderme"


def _solicitud(**campos: object) -> SolicitudDeEvaluacion:
    return EvaluacionRequest.model_validate({"texto": TEXTO, **campos}).a_solicitud()


def test_el_cuerpo_minimo_solo_lleva_el_texto() -> None:
    solicitud = _solicitud()

    assert solicitud.texto == TEXTO
    assert (
        solicitud.contexto.entidades,
        solicitud.contexto.establecimiento_conocido,
        solicitud.contexto.tiene_archivos,
    ) == (
        None,
        False,
        False,
    )
    assert (solicitud.combinar_con_ia, solicitud.peso_ia) == (False, None)


def test_el_texto_no_se_recorta_y_los_campos_desconocidos_se_ignoran() -> None:
    solicitud = _solicitud(texto=f"  {TEXTO}  ", otro=1)

    assert solicitud.texto == f"  {TEXTO}  "


def test_el_contexto_trae_las_entidades_recortadas_con_sus_alias() -> None:
    entidades = [{"codigo": " x ", "nombre": " Clinica X ", "alias": [" CX "]}, {"codigo": "y", "nombre": "Y"}]

    contexto = _solicitud(entidades=entidades, establecimientoConocido=True, tieneArchivos=True).contexto

    assert contexto.entidades is not None
    assert [(e.codigo, e.nombre, e.alias) for e in contexto.entidades] == [("x", "Clinica X", ("CX",)), ("y", "Y", ())]
    assert (contexto.establecimiento_conocido, contexto.tiene_archivos) == (True, True)


def test_una_lista_vacia_de_entidades_se_conserva_para_apagar_la_deteccion() -> None:
    assert _solicitud(entidades=[]).contexto.entidades == ()


@pytest.mark.parametrize("peso", [6, 6.5, 0, -3, None])
def test_el_peso_de_la_ia_pedido_aunque_sea_nulo_activa_la_combinacion(peso: float | None) -> None:
    solicitud = _solicitud(pesoIa=peso)

    assert (solicitud.combinar_con_ia, solicitud.peso_ia) == (True, peso)


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"texto": 5},
        {"texto": None},
        {"texto": "x" * 5001},
        {"texto": "😀" * 2501},
        {"texto": TEXTO, "entidades": [{}]},
        {"texto": TEXTO, "entidades": [{"codigo": "  ", "nombre": "X"}]},
        {"texto": TEXTO, "entidades": [{"codigo": "x" * 51, "nombre": "X"}]},
        {"texto": TEXTO, "entidades": [{"codigo": "x", "nombre": "n" * 201}]},
        {"texto": TEXTO, "entidades": [{"codigo": "x", "nombre": "X", "alias": [" "]}]},
        {"texto": TEXTO, "entidades": [{"codigo": "x", "nombre": "X", "alias": ["a"] * 21}]},
        {"texto": TEXTO, "entidades": [{"codigo": "x", "nombre": "X"}] * 101},
        {"texto": TEXTO, "establecimientoConocido": "si"},
        {"texto": TEXTO, "tieneArchivos": 1},
        {"texto": TEXTO, "pesoIa": "6"},
        {"texto": TEXTO, "pesoIa": True},
    ],
)
def test_un_cuerpo_invalido_se_rechaza(cuerpo: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EvaluacionRequest.model_validate(cuerpo)


def test_el_texto_de_5000_unidades_exactas_es_valido_y_el_largo_se_mide_en_utf16() -> None:
    assert _solicitud(texto="x" * 5000).texto == "x" * 5000
    assert _solicitud(texto="😀" * 2500).texto == "😀" * 2500


def test_la_respuesta_sin_combinacion_no_marca_ese_campo_como_enviado() -> None:
    evaluacion = EvaluarCorrupcion().execute(_solicitud())

    cuerpo = EvaluacionCorrupcionResponse.desde_dominio(evaluacion).model_dump(
        by_alias=True, mode="json", exclude_unset=True
    )

    assert "combinacion" not in cuerpo
    assert cuerpo["propuestaCorrupcion"] is True
    assert cuerpo["entidad"] == {"codigo": "sis", "nombre": "Seguro Integral de Salud", "tipo": "SIS"}


def test_la_respuesta_con_combinacion_la_incluye_aunque_el_peso_sea_nulo() -> None:
    evaluacion = EvaluarCorrupcion().execute(_solicitud(pesoIa=None))

    cuerpo = EvaluacionCorrupcionResponse.desde_dominio(evaluacion).model_dump(
        by_alias=True, mode="json", exclude_unset=True
    )

    assert cuerpo["combinacion"]["pesoIa"] is None
    assert cuerpo["combinacion"]["acuerdo"] == "SIN_MODELO"


@pytest.mark.parametrize("peso", [float("nan"), float("inf"), float("-inf")])
def test_el_peso_de_la_ia_no_puede_ser_infinito_ni_indefinido(peso: float) -> None:
    with pytest.raises(ValidationError):
        EvaluacionRequest.model_validate({"texto": TEXTO, "pesoIa": peso})
