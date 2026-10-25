import json
from pathlib import Path

from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.contract import openapi_del_nodo, validar_contrato

CONTRATO_DEL_NODO = Path(__file__).parents[2] / "docs" / "contrato" / "v1.json"
RUTA = "/v1/catalogos/plazos"


async def test_la_respuesta_cumple_el_contrato_del_backend_node() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        validar_contrato(openapi_del_nodo(), await cliente.get(RUTA))


def test_la_operacion_existe_en_el_contrato_del_backend_node_con_sesion_obligatoria() -> None:
    contrato = json.loads(CONTRATO_DEL_NODO.read_text(encoding="utf-8"))

    operacion = contrato["paths"]["/catalogos/plazos"]["get"]

    assert operacion["operationId"] == "listarPlazosPorCategoria"
    assert "401" in operacion["responses"]
