import json
from pathlib import Path

import pytest

from app.incidencias.domain.derivaciones import ConteosDeDerivaciones
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_caso_consultado, una_derivacion_consultada, una_evidencia, una_sesion
from tests.helpers.casos import IMAGEN_PNG
from tests.helpers.contract import openapi_del_nodo, validar_contrato
from tests.helpers.derivaciones_en_memoria import DerivacionesEnMemoria
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

CONTRATO_DEL_NODO = Path(__file__).parents[2] / "docs" / "contrato" / "v1.json"
RUTA = "/v1/derivaciones"
CODIGO = "MINSA-2026-000001"
EVIDENCIA = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"
OTRANS = una_sesion(roles=("OTRANS",))


@pytest.mark.parametrize(
    ("ruta", "operacion"),
    [
        ("/derivaciones", "listarDerivaciones"),
        ("/derivaciones/conteos", "contarDerivaciones"),
        ("/derivaciones/{codigo}", "obtenerDerivacion"),
        ("/derivaciones/{codigo}/evidencias/{evidenciaId}/contenido", "obtenerContenidoDeEvidenciaDerivada"),
    ],
)
def test_las_operaciones_existen_en_el_contrato_del_node_con_el_mismo_identificador(ruta: str, operacion: str) -> None:
    contrato = json.loads(CONTRATO_DEL_NODO.read_text(encoding="utf-8"))

    assert contrato["paths"][ruta]["get"]["operationId"] == operacion


def _contenedor() -> object:
    envios = DerivacionesEnMemoria([una_derivacion_consultada()])
    envios.conteos = ConteosDeDerivaciones(4, 1, 1, 1, 1)
    casos = IncidenciasEnMemoria([un_caso_consultado()], evidencias=[una_evidencia()], rutas={EVIDENCIA: IMAGEN_PNG})
    return un_contenedor(derivaciones=envios, incidencias=casos)


async def test_las_lecturas_felices_cumplen_el_contrato_del_node() -> None:
    async with un_cliente(_contenedor(), sesion=OTRANS) as cliente:  # type: ignore[arg-type]
        for ruta in (RUTA, f"{RUTA}/conteos", f"{RUTA}/{CODIGO}"):
            respuesta = await cliente.get(ruta)
            assert respuesta.status_code == 200, ruta
            validar_contrato(openapi_del_nodo(), respuesta)
        validar_contrato(openapi_del_nodo(), await cliente.get(f"{RUTA}/{CODIGO}/evidencias/{EVIDENCIA}/contenido"))


async def test_los_errores_cumplen_el_contrato_del_node() -> None:
    contenedor = _contenedor()
    async with un_cliente(contenedor, sesion=OTRANS) as cliente:  # type: ignore[arg-type]
        for ruta in (
            f"{RUTA}?limite=0",
            f"{RUTA}?categoria=sin-categoria",
            f"{RUTA}/conteos?desde=x",
            f"{RUTA}/MINSA-2026-000099",
            f"{RUTA}/no-es-un-codigo",
            f"{RUTA}/{CODIGO}/evidencias/{EVIDENCIA.upper()}/contenido",
        ):
            validar_contrato(openapi_del_nodo(), await cliente.get(ruta))
    async with un_cliente(contenedor, sesion=una_sesion(roles=("GESTOR",))) as sin_acceso:  # type: ignore[arg-type]
        validar_contrato(openapi_del_nodo(), await sin_acceso.get(RUTA))
    async with un_cliente(contenedor, con_sesion=False) as anonimo:  # type: ignore[arg-type]
        validar_contrato(openapi_del_nodo(), await anonimo.get(RUTA))
