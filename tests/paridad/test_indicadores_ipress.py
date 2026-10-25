import json
from pathlib import Path

import pytest

from app.composition import Container
from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.domain.ipress import IpressConsultada, IpressListada
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_caso_consultado, una_evidencia, una_sesion
from tests.helpers.casos import IMAGEN_PNG
from tests.helpers.contract import openapi_del_nodo, validar_contrato
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria
from tests.helpers.indicadores_en_memoria import IndicadoresEnMemoria, IpressEnMemoria

CONTRATO_DEL_NODO = Path(__file__).parents[2] / "docs" / "contrato" / "v1.json"
RAIZ = "/v1/consulta-ipress"
RENIPRESS = "1234"
CODIGO = "MINSA-2026-000001"
EVIDENCIA = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"
ADMIN = una_sesion(roles=("ADMINISTRADOR",))
OPERACIONES = [
    ("/indicadores", "obtenerIndicadores"),
    ("/consulta-ipress/establecimientos", "buscarIpress"),
    ("/consulta-ipress/{renipress}/indicadores", "obtenerIndicadoresDeIpress"),
    ("/consulta-ipress/{renipress}/resumen", "obtenerResumenDeIpress"),
    ("/consulta-ipress/{renipress}/incidencias", "listarIncidenciasDeIpress"),
    ("/consulta-ipress/{renipress}/conteos", "contarIncidenciasDeIpress"),
    ("/consulta-ipress/{renipress}/incidencias/{codigo}", "obtenerIncidenciaDeIpress"),
    (
        "/consulta-ipress/{renipress}/incidencias/{codigo}/evidencias/{evidenciaId}/contenido",
        "obtenerContenidoDeEvidenciaDeIpress",
    ),
]


@pytest.mark.parametrize(("ruta", "operacion"), OPERACIONES)
def test_las_operaciones_existen_en_el_contrato_del_node_con_el_mismo_identificador(ruta: str, operacion: str) -> None:
    contrato = json.loads(CONTRATO_DEL_NODO.read_text(encoding="utf-8"))

    assert contrato["paths"][ruta]["get"]["operationId"] == operacion


def _contenedor() -> Container:
    casos = IncidenciasEnMemoria([un_caso_consultado()], evidencias=[una_evidencia()], rutas={EVIDENCIA: IMAGEN_PNG})
    casos.por_estado = {EstadoIncidencia.CLASIFICADO: 1}
    ipress = IpressEnMemoria(
        {RENIPRESS: IpressConsultada(7, "EESS-0001", "Centro de Salud")},
        [IpressListada(3, "EESS-0001", "Centro de Salud", "1234", "I", "I-3")],
    )
    return un_contenedor(incidencias=casos, ipress=ipress, indicadores=IndicadoresEnMemoria())


async def test_los_indicadores_cumplen_el_contrato_del_node() -> None:
    async with un_cliente(_contenedor(), sesion=ADMIN) as cliente:
        for periodo in ("7d", "30d", "90d"):
            respuesta = await cliente.get("/v1/indicadores", params={"periodo": periodo})
            assert respuesta.status_code == 200, periodo
            validar_contrato(openapi_del_nodo(), respuesta)
        validar_contrato(openapi_del_nodo(), await cliente.get("/v1/indicadores", params={"periodo": "15d"}))


async def test_las_lecturas_de_ipress_cumplen_el_contrato_del_node() -> None:
    async with un_cliente(_contenedor(), sesion=ADMIN) as cliente:
        for ruta in (
            f"{RAIZ}/establecimientos",
            f"{RAIZ}/{RENIPRESS}/indicadores",
            f"{RAIZ}/{RENIPRESS}/resumen",
            f"{RAIZ}/{RENIPRESS}/incidencias",
            f"{RAIZ}/{RENIPRESS}/conteos",
            f"{RAIZ}/{RENIPRESS}/incidencias/{CODIGO}",
        ):
            respuesta = await cliente.get(ruta)
            assert respuesta.status_code == 200, ruta
            validar_contrato(openapi_del_nodo(), respuesta)
        evidencia = await cliente.get(f"{RAIZ}/{RENIPRESS}/incidencias/{CODIGO}/evidencias/{EVIDENCIA}/contenido")
        validar_contrato(openapi_del_nodo(), evidencia)


async def test_los_errores_de_ipress_cumplen_el_contrato_del_node() -> None:
    async with un_cliente(_contenedor(), sesion=ADMIN) as cliente:
        for ruta in (
            f"{RAIZ}/establecimientos?limite=0",
            f"{RAIZ}/abc/resumen",
            f"{RAIZ}/9999/indicadores",
            f"{RAIZ}/{RENIPRESS}/incidencias?limite=0",
            f"{RAIZ}/{RENIPRESS}/conteos?desde=x",
            f"{RAIZ}/{RENIPRESS}/incidencias/MINSA-2026-000099",
            f"{RAIZ}/{RENIPRESS}/incidencias/{CODIGO}/evidencias/{EVIDENCIA.upper()}/contenido",
        ):
            validar_contrato(openapi_del_nodo(), await cliente.get(ruta))
    async with un_cliente(_contenedor(), sesion=una_sesion(roles=("GESTOR",))) as sin_acceso:
        validar_contrato(openapi_del_nodo(), await sin_acceso.get(f"{RAIZ}/establecimientos"))
    async with un_cliente(_contenedor(), con_sesion=False) as anonimo:
        validar_contrato(openapi_del_nodo(), await anonimo.get("/v1/indicadores"))
