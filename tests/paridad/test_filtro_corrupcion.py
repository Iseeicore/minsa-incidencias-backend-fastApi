import json
from pathlib import Path
from typing import Any

import pytest

from app.filtro_corrupcion.adapters.http.schemas import EvaluacionCorrupcionResponse, EvaluacionRequest
from app.filtro_corrupcion.application.evaluar_corrupcion import EvaluarCorrupcion
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import una_sesion
from tests.helpers.contract import openapi_del_nodo, validar_contrato

CORPUS_DEL_NODO = Path(__file__).parents[1] / "fixtures" / "corpus_corrupcion_node.json"
CONTRATO_DEL_NODO = Path(__file__).parents[2] / "docs" / "contrato" / "v1.json"
RUTA = "/v1/filtro-corrupcion/evaluar"
GESTOR = una_sesion(roles=("GESTOR",))


def _casos() -> list[dict[str, Any]]:
    casos: list[dict[str, Any]] = json.loads(CORPUS_DEL_NODO.read_text(encoding="utf-8"))
    return casos


def _cuerpo(entrada: dict[str, Any]) -> dict[str, Any]:
    cuerpo = {"texto": entrada["texto"], **entrada["contexto"]}
    if "pesoIa" in entrada:
        cuerpo["pesoIa"] = entrada["pesoIa"]
    return cuerpo


def test_la_operacion_existe_en_el_contrato_del_node_con_el_mismo_identificador() -> None:
    contrato = json.loads(CONTRATO_DEL_NODO.read_text(encoding="utf-8"))

    assert contrato["paths"]["/filtro-corrupcion/evaluar"]["post"]["operationId"] == "evaluarTextoCorrupcion"


def test_el_corpus_de_oro_cubre_las_ramas_importantes_del_motor() -> None:
    esperados = [caso["esperado"] for caso in _casos()]

    assert len(esperados) > 800
    assert {e["origenPropuesta"] for e in esperados} == {None, "REGLAS", "IDENTIDAD"}
    assert {e["certeza"] for e in esperados} == {"ALTA", "MEDIA", "BAJA"}
    assert any(e["requiereSegundaOpinion"] for e in esperados)
    assert any(e["senalSensible"] == "ACOSO" and e["escalarAOtrans"] for e in esperados)
    assert any(e["identidad"]["viaEntidad"] == "NOMBRE_TITULAR" for e in esperados)
    assert any(e["identidad"]["ubicacion"] is not None for e in esperados)
    assert any("combinacion" in e for e in esperados)
    assert any(not e["aplica"] for e in esperados)


def test_el_motor_responde_exactamente_lo_mismo_que_el_node_en_todo_el_corpus() -> None:
    distintos: list[int] = []
    for numero, caso in enumerate(_casos()):
        solicitud = EvaluacionRequest.model_validate(_cuerpo(caso["entrada"])).a_solicitud()
        obtenido = EvaluacionCorrupcionResponse.desde_dominio(EvaluarCorrupcion().execute(solicitud))
        if obtenido.model_dump(by_alias=True, mode="json", exclude_unset=True) != caso["esperado"]:
            distintos.append(numero)

    assert distintos == []


@pytest.mark.parametrize("paso", range(0, 835, 40))
async def test_la_respuesta_http_cumple_el_contrato_del_node_y_coincide_con_el_corpus(paso: int) -> None:
    caso = _casos()[paso]
    async with un_cliente(un_contenedor(), sesion=GESTOR) as cliente:
        respuesta = await cliente.post(RUTA, json=_cuerpo(caso["entrada"]))

    assert respuesta.status_code == 200
    assert respuesta.json() == caso["esperado"]
    validar_contrato(openapi_del_nodo(), respuesta)


async def test_los_errores_cumplen_el_contrato_del_node() -> None:
    async with un_cliente(un_contenedor(), sesion=GESTOR) as cliente:
        for cuerpo in ({}, {"texto": 5}, {"texto": "x" * 5001}, {"texto": "ok" * 20, "pesoIa": "6"}):
            validar_contrato(openapi_del_nodo(), await cliente.post(RUTA, json=cuerpo))
    async with un_cliente(un_contenedor(), sesion=una_sesion(roles=("ESTABLECIMIENTO",))) as sin_rol:
        validar_contrato(openapi_del_nodo(), await sin_rol.post(RUTA, json={"texto": "ok" * 20}))
    async with un_cliente(un_contenedor(), con_sesion=False) as anonimo:
        validar_contrato(openapi_del_nodo(), await anonimo.post(RUTA, json={"texto": "ok" * 20}))
