import json
from pathlib import Path

import pytest

from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.domain.caso_consultado import ConteoPorVencer
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_caso_consultado, una_evidencia, una_sesion
from tests.helpers.casos import IMAGEN_PNG
from tests.helpers.contract import openapi_del_nodo, validar_contrato
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

CONTRATO_DEL_NODO = Path(__file__).parents[2] / "docs" / "contrato" / "v1.json"
RUTA = "/v1/incidencias"
CODIGO = "MINSA-2026-000001"
EVIDENCIA = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"


@pytest.mark.parametrize(
    ("ruta", "operacion"),
    [
        ("/incidencias", "listarIncidencias"),
        ("/incidencias/conteos", "contarIncidencias"),
        ("/incidencias/por-vencer", "consultarIncidenciasPorVencer"),
        ("/incidencias/{codigo}", "obtenerIncidencia"),
        ("/incidencias/{codigo}/evidencias/{evidenciaId}/contenido", "obtenerContenidoDeEvidencia"),
    ],
)
def test_las_operaciones_existen_en_el_contrato_del_node_con_el_mismo_identificador(ruta: str, operacion: str) -> None:
    contrato = json.loads(CONTRATO_DEL_NODO.read_text(encoding="utf-8"))

    assert contrato["paths"][ruta]["get"]["operationId"] == operacion


def _lector() -> IncidenciasEnMemoria:
    lector = IncidenciasEnMemoria([un_caso_consultado()], evidencias=[una_evidencia()], rutas={EVIDENCIA: IMAGEN_PNG})
    lector.por_estado = {EstadoIncidencia.CLASIFICADO: 1}
    lector.conteo_por_vencer = ConteoPorVencer(1, 0)
    return lector


async def test_las_lecturas_felices_cumplen_el_contrato_del_node() -> None:
    contenedor = un_contenedor(incidencias=_lector())
    async with un_cliente(contenedor, sesion=una_sesion(roles=("ADMINISTRADOR",))) as cliente:
        for ruta in (RUTA, f"{RUTA}/conteos", f"{RUTA}/por-vencer", f"{RUTA}/{CODIGO}"):
            respuesta = await cliente.get(ruta)
            assert respuesta.status_code == 200, ruta
            validar_contrato(openapi_del_nodo(), respuesta)
        validar_contrato(openapi_del_nodo(), await cliente.get(f"{RUTA}/{CODIGO}/evidencias/{EVIDENCIA}/contenido"))


async def test_los_errores_cumplen_el_contrato_del_node() -> None:
    contenedor = un_contenedor(incidencias=_lector())
    async with un_cliente(contenedor, sesion=una_sesion(roles=("ADMINISTRADOR",))) as cliente:
        for ruta in (
            f"{RUTA}?limite=0",
            f"{RUTA}/conteos?desde=x",
            f"{RUTA}/MINSA-2026-000099",
            f"{RUTA}/{CODIGO}/evidencias/{EVIDENCIA.upper()}/contenido",
        ):
            validar_contrato(openapi_del_nodo(), await cliente.get(ruta))
    async with un_cliente(contenedor, sesion=una_sesion(roles=())) as sin_vistas:
        validar_contrato(openapi_del_nodo(), await sin_vistas.get(RUTA))
    async with un_cliente(contenedor, con_sesion=False) as anonimo:
        validar_contrato(openapi_del_nodo(), await anonimo.get(RUTA))
