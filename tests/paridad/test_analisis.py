import json
from pathlib import Path

import pytest

from tests.helpers.analisis_en_memoria import AnalisisEnMemoria, una_fila_de_analisis
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_caso_consultado, una_sesion
from tests.helpers.contract import openapi_del_nodo, validar_contrato
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

CONTRATO_DEL_NODO = Path(__file__).parents[2] / "docs" / "contrato" / "v1.json"
CODIGO = "MINSA-2026-000001"
ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTRANS = una_sesion(roles=("OTRANS",))
SENALES = {
    "senales": [{"frase": "me pidió plata", "tipo": "FUERTE", "peso": 3}],
    "explicacion": "Pedido de dinero.",
    "informacionFaltante": ["pruebas", "autor_o_cargo"],
    "fichaDerivacion": {
        "codigoEntidad": "sis",
        "contactosDisponibles": ["OCI"],
        "destinoSiTitular": {"texto": "A la PCM", "entidadDestinoCodigo": None},
        "aplicaAlTitular": False,
    },
    "normas": {
        "version": "normas-v1",
        "citas": [
            {"fragmentoId": "ANEXO_C-III-a", "referencia": "x", "grupo": "SUPUESTO", "senalesQueLaMotivan": ["a"]},
            {"fragmentoId": "AM-DERIVA-STPAD-OCI-PP", "referencia": "y", "grupo": "PROCEDIMIENTO"},
        ],
    },
    "decision": {"motivo": "REGLAS", "propuestaDelAnalisis": "DENUNCIA_CORRUPCION", "pesoIa": None},
    "modelo": {"variante": None, "degradado": False},
}


@pytest.mark.parametrize(
    ("ruta", "operacion"),
    [
        ("/incidencias/{codigo}/clasificacion", "obtenerClasificacion"),
        ("/incidencias/{codigo}/analisis-ia", "obtenerAnalisisIa"),
    ],
)
def test_las_operaciones_existen_en_el_contrato_del_node_con_el_mismo_identificador(ruta: str, operacion: str) -> None:
    contrato = json.loads(CONTRATO_DEL_NODO.read_text(encoding="utf-8"))

    assert contrato["paths"][ruta]["get"]["operationId"] == operacion


def _contenedor(*, con_analisis: bool = True) -> object:
    analisis = AnalisisEnMemoria({ID: una_fila_de_analisis(senales=SENALES)} if con_analisis else {})
    return un_contenedor(incidencias=IncidenciasEnMemoria([un_caso_consultado()]), analisis=analisis)


@pytest.mark.parametrize("sufijo", ["clasificacion", "analisis-ia"])
async def test_el_analisis_guardado_cumple_el_contrato_del_node(sufijo: str) -> None:
    async with un_cliente(_contenedor(), sesion=OTRANS) as cliente:  # type: ignore[arg-type]
        respuesta = await cliente.get(f"/v1/incidencias/{CODIGO}/{sufijo}")

    assert respuesta.status_code == 200
    validar_contrato(openapi_del_nodo(), respuesta)


@pytest.mark.parametrize("sufijo", ["clasificacion", "analisis-ia"])
async def test_los_errores_cumplen_el_contrato_del_node(sufijo: str) -> None:
    async with un_cliente(_contenedor(con_analisis=False), sesion=OTRANS) as sin_analisis:  # type: ignore[arg-type]
        validar_contrato(openapi_del_nodo(), await sin_analisis.get(f"/v1/incidencias/{CODIGO}/{sufijo}"))
        validar_contrato(openapi_del_nodo(), await sin_analisis.get(f"/v1/incidencias/no-es-un-codigo/{sufijo}"))
    async with un_cliente(_contenedor(), sesion=una_sesion(roles=("GESTOR",))) as sin_rol:  # type: ignore[arg-type]
        validar_contrato(openapi_del_nodo(), await sin_rol.get(f"/v1/incidencias/{CODIGO}/{sufijo}"))
    async with un_cliente(_contenedor(), con_sesion=False) as anonimo:  # type: ignore[arg-type]
        validar_contrato(openapi_del_nodo(), await anonimo.get(f"/v1/incidencias/{CODIGO}/{sufijo}"))
