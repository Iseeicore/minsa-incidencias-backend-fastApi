import json
from pathlib import Path
from typing import Any

import pytest

from app.composition import create_v1_app
from tests.helpers.app_factory import un_contenedor

type Spec = dict[str, Any]

CONTRATO_DEL_NODO = Path(__file__).parents[2] / "docs" / "contrato" / "v1.json"
METODOS = ("get", "post", "put", "patch", "delete")
PROFUNDIDAD_MAXIMA = 6
NULO = {"type": "null"}


def _operaciones(spec: Spec) -> dict[tuple[str, str], Spec]:
    return {
        (metodo.upper(), ruta): operacion
        for ruta, item in spec["paths"].items()
        for metodo, operacion in item.items()
        if metodo in METODOS
    }


def _resolver(spec: Spec, nodo: Any) -> Any:  # noqa: ANN401
    while isinstance(nodo, dict) and "$ref" in nodo:
        nodo = spec["components"]["schemas"][nodo["$ref"].rsplit("/", 1)[1]]
    return nodo


def _forma_de_union(spec: Spec, partes: list[Any], profundidad: int) -> Any:  # noqa: ANN401
    formas = [_forma(spec, parte, profundidad) for parte in partes if parte != NULO]
    return next((forma for forma in formas if forma is not None), None)


def _forma_combinada(spec: Spec, partes: list[Any], profundidad: int) -> Any:  # noqa: ANN401
    propiedades: dict[str, Any] = {}
    requeridas: set[str] = set()
    for parte in partes:
        forma = _forma(spec, parte, profundidad)
        if isinstance(forma, dict) and "propiedades" in forma:
            propiedades |= forma["propiedades"]
            requeridas |= forma["requeridas"]
    return {"propiedades": propiedades, "requeridas": requeridas}


def _forma(spec: Spec, esquema: Any, profundidad: int = 0) -> Any:  # noqa: ANN401
    esquema = _resolver(spec, esquema)
    if not isinstance(esquema, dict) or profundidad > PROFUNDIDAD_MAXIMA:
        return None
    for union in ("anyOf", "oneOf"):
        if union in esquema:
            return _forma_de_union(spec, esquema[union], profundidad)
    if "allOf" in esquema:
        return _forma_combinada(spec, esquema["allOf"], profundidad)
    if esquema.get("type") == "array":
        return {"items": _forma(spec, esquema.get("items", {}), profundidad + 1)}
    if "properties" in esquema:
        propiedades = {nombre: _forma(spec, sub, profundidad + 1) for nombre, sub in esquema["properties"].items()}
        return {"propiedades": propiedades, "requeridas": set(esquema.get("required", []))}
    return None


def _cuerpo(spec: Spec, contenido: Spec | None) -> Any:  # noqa: ANN401
    if not contenido or "application/json" not in contenido:
        return "sin-json"
    return _forma(spec, contenido["application/json"].get("schema", {}))


def _parametros(spec: Spec, operacion: Spec) -> dict[tuple[str, str], bool]:
    resultado: dict[tuple[str, str], bool] = {}
    for parametro in operacion.get("parameters", []):
        if "$ref" in parametro:
            parametro = spec["components"]["parameters"][parametro["$ref"].rsplit("/", 1)[1]]  # noqa: PLW2901
        resultado[(parametro["in"], parametro["name"])] = bool(parametro.get("required"))
    return resultado


REFERENCIA: Spec = json.loads(CONTRATO_DEL_NODO.read_text(encoding="utf-8"))
PROPIA: Spec = create_v1_app(un_contenedor()).openapi()
OPERACIONES_DE_REFERENCIA = _operaciones(REFERENCIA)
OPERACIONES_PROPIAS = _operaciones(PROPIA)
IDS = [f"{metodo} {ruta}" for metodo, ruta in OPERACIONES_DE_REFERENCIA]


def test_la_aplicacion_expone_exactamente_las_operaciones_del_contrato_del_node() -> None:
    assert set(OPERACIONES_PROPIAS) == set(OPERACIONES_DE_REFERENCIA)
    assert len(OPERACIONES_DE_REFERENCIA) == 37


def test_el_prefijo_y_la_version_son_los_del_contrato() -> None:
    assert PROPIA["servers"] == REFERENCIA["servers"] == [{"url": "/v1"}]
    assert PROPIA["info"]["version"] == REFERENCIA["info"]["version"]


@pytest.mark.parametrize("clave", list(OPERACIONES_DE_REFERENCIA), ids=IDS)
def test_cada_operacion_conserva_su_identificador_y_sus_codigos_de_respuesta(clave: tuple[str, str]) -> None:
    referencia, propia = OPERACIONES_DE_REFERENCIA[clave], OPERACIONES_PROPIAS[clave]

    assert propia["operationId"] == referencia["operationId"]
    assert set(propia["responses"]) == set(referencia["responses"])


@pytest.mark.parametrize("clave", list(OPERACIONES_DE_REFERENCIA), ids=IDS)
def test_cada_operacion_conserva_sus_parametros_y_si_son_obligatorios(clave: tuple[str, str]) -> None:
    referencia, propia = OPERACIONES_DE_REFERENCIA[clave], OPERACIONES_PROPIAS[clave]

    assert _parametros(PROPIA, propia) == _parametros(REFERENCIA, referencia)


@pytest.mark.parametrize("clave", list(OPERACIONES_DE_REFERENCIA), ids=IDS)
def test_cada_operacion_conserva_la_forma_de_su_cuerpo_de_peticion(clave: tuple[str, str]) -> None:
    referencia, propia = OPERACIONES_DE_REFERENCIA[clave], OPERACIONES_PROPIAS[clave]

    assert ("requestBody" in propia) == ("requestBody" in referencia)
    if "requestBody" in referencia:
        assert _cuerpo(PROPIA, propia["requestBody"]["content"]) == _cuerpo(
            REFERENCIA, referencia["requestBody"]["content"]
        )


@pytest.mark.parametrize("clave", list(OPERACIONES_DE_REFERENCIA), ids=IDS)
def test_cada_respuesta_de_exito_conserva_la_forma_de_su_cuerpo(clave: tuple[str, str]) -> None:
    referencia, propia = OPERACIONES_DE_REFERENCIA[clave], OPERACIONES_PROPIAS[clave]

    for codigo in (c for c in referencia["responses"] if c.startswith("2")):
        esperada = _cuerpo(REFERENCIA, referencia["responses"][codigo].get("content"))
        obtenida = _cuerpo(PROPIA, propia["responses"][codigo].get("content"))
        assert obtenida == esperada, codigo


def test_la_comparacion_de_formas_no_es_vacua() -> None:
    con_forma = [
        clave
        for clave, operacion in OPERACIONES_DE_REFERENCIA.items()
        for codigo, respuesta in operacion["responses"].items()
        if codigo.startswith("2") and _cuerpo(REFERENCIA, respuesta.get("content")) not in (None, "sin-json")
    ]

    assert len(con_forma) >= 20
