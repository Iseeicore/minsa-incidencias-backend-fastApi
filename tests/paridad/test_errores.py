import json
from pathlib import Path
from typing import Any

from app.enums.error_code import ErrorCode
from app.shared.http_errors import HTTP_STATUS_BY_CATEGORY, ErrorBody
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.contract import openapi_del_nodo, validar_contrato

CONTRATO_DEL_NODO = Path(__file__).parents[2] / "docs" / "contrato" / "v1.json"
RUTA = "/v1/catalogos/plazos"


def _error_del_nodo() -> dict[str, Any]:
    contrato = json.loads(CONTRATO_DEL_NODO.read_text(encoding="utf-8"))
    esquema: dict[str, Any] = contrato["components"]["schemas"]["ErrorPayload"]
    return esquema


def test_los_codigos_de_error_son_exactamente_los_del_contrato_del_node() -> None:
    codigos = _error_del_nodo()["properties"]["errorCode"]["enum"]

    assert [codigo.value for codigo in ErrorCode] == codigos


def test_los_estados_de_las_categorias_estan_en_el_contrato_del_node() -> None:
    estados = set(_error_del_nodo()["properties"]["statusCode"]["enum"])

    assert {int(estado) for estado in HTTP_STATUS_BY_CATEGORY.values()} <= estados


def test_el_cuerpo_de_error_declara_los_mismos_campos_que_el_contrato_del_node() -> None:
    campos_del_nodo = set(_error_del_nodo()["properties"])

    campos_propios = {campo.serialization_alias or nombre for nombre, campo in ErrorBody.model_fields.items()}

    assert campos_propios == campos_del_nodo


async def test_el_401_sin_sesion_cumple_el_contrato_del_node() -> None:
    async with un_cliente(un_contenedor(), con_sesion=False) as cliente:
        respuesta = await cliente.get(RUTA)

    validar_contrato(openapi_del_nodo(), respuesta)
    assert respuesta.json()["message"] == "Debes iniciar sesión."
