from typing import Any

import pytest

from app.composition import create_app, create_v1_app
from app.enums.error_code import ErrorCode
from tests.helpers.app_factory import un_contenedor

type Spec = dict[str, Any]

METODOS = {"get", "post", "put", "patch", "delete"}
ESQUEMA_DE_ERROR = "#/components/schemas/ErrorBody"
ESQUEMA_DE_SALUD = "#/components/schemas/HealthResponse"
ESTADOS_DE_ERROR = {"400", "401", "403", "404", "409", "413", "422", "429", "500", "503"}
SIN_CABECERA_LOCATION = {"crearUsuario": "el contrato del Node devuelve el usuario creado en el cuerpo"}


def _especificaciones() -> dict[str, Spec]:
    contenedor = un_contenedor()
    return {"raiz": create_app(contenedor).openapi(), "v1": create_v1_app(contenedor).openapi()}


def _operaciones() -> list[tuple[str, str, Spec]]:
    return [
        (f"{nombre} {metodo.upper()} {ruta}", nombre, operacion)
        for nombre, especificacion in _especificaciones().items()
        for ruta, item in especificacion["paths"].items()
        for metodo, operacion in item.items()
        if metodo in METODOS
    ]


OPERACIONES = _operaciones()
IDS = [identificador for identificador, _, _ in OPERACIONES]


def _esquema_de(respuesta: Spec) -> str | None:
    contenido = respuesta.get("content", {}).get("application/json", {})
    referencia = contenido.get("schema", {}).get("$ref")
    return referencia if isinstance(referencia, str) else None


@pytest.mark.parametrize("operacion", [operacion for _, _, operacion in OPERACIONES], ids=IDS)
def test_cada_operacion_tiene_resumen_descripcion_y_etiqueta(operacion: Spec) -> None:
    assert operacion.get("summary")
    assert operacion.get("description")
    assert operacion.get("tags")


@pytest.mark.parametrize("operacion", [operacion for _, _, operacion in OPERACIONES], ids=IDS)
def test_cada_operacion_documenta_el_error_500_en_el_formato_unico(operacion: Spec) -> None:
    assert _esquema_de(operacion["responses"]["500"]) == ESQUEMA_DE_ERROR


@pytest.mark.parametrize("operacion", [operacion for _, _, operacion in OPERACIONES], ids=IDS)
def test_cada_error_documentado_usa_el_formato_unico(operacion: Spec) -> None:
    for estado, respuesta in operacion["responses"].items():
        if estado in ESTADOS_DE_ERROR:
            assert _esquema_de(respuesta) in {ESQUEMA_DE_ERROR, ESQUEMA_DE_SALUD}, estado


@pytest.mark.parametrize("operacion", [operacion for _, _, operacion in OPERACIONES], ids=IDS)
def test_un_201_declara_la_cabecera_location(operacion: Spec) -> None:
    if "201" in operacion["responses"] and operacion["operationId"] not in SIN_CABECERA_LOCATION:
        assert "Location" in operacion["responses"]["201"]["headers"]


@pytest.mark.parametrize("operacion", [operacion for _, _, operacion in OPERACIONES], ids=IDS)
def test_cada_exito_y_cada_error_traen_ejemplo(operacion: Spec) -> None:
    for estado, respuesta in operacion["responses"].items():
        if estado == "204" or "application/json" not in respuesta.get("content", {}):
            continue
        contenido = respuesta["content"]["application/json"]
        assert "example" in contenido or "examples" in contenido, estado


def test_todos_los_codigos_de_error_estan_documentados() -> None:
    esquemas = _especificaciones()["v1"]["components"]["schemas"]

    assert esquemas["ErrorBody"]["properties"]["errorCode"]["$ref"] == "#/components/schemas/ErrorCode"
    assert set(esquemas["ErrorCode"]["enum"]) == {codigo.value for codigo in ErrorCode}
