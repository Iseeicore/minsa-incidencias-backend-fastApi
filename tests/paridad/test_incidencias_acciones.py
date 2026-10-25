import json
from pathlib import Path

import pytest

from app.enums.estado_incidencia import EstadoIncidencia
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_caso_consultado, una_evidencia, una_sesion
from tests.helpers.contract import openapi_del_nodo, validar_contrato
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

CONTRATO_DEL_NODO = Path(__file__).parents[2] / "docs" / "contrato" / "v1.json"
RUTA = "/v1/incidencias/MINSA-2026-000001"
TEXTO = "Texto de al menos diez"
CUERPOS: dict[str, dict[str, object] | None] = {
    "confirmar": None,
    "corregir": {"categoria": "queja"},
    "derivar": {"descripcionDerivacion": TEXTO},
    "tomar": None,
    "resolver": {"medidasTomadas": TEXTO, "fundamento": TEXTO, "resultado": "ATENDIDO"},
    "archivar": {"motivo": "NO_CORRESPONDE", "detalle": TEXTO},
    "reabrir": {"motivo": TEXTO},
}
OPERACIONES = {
    "confirmar": "confirmarCategoria",
    "corregir": "corregirCategoria",
    "derivar": "derivarIncidencia",
    "tomar": "tomarIncidencia",
    "resolver": "resolverIncidencia",
    "archivar": "archivarIncidencia",
    "reabrir": "reabrirIncidencia",
}
ADMIN = una_sesion(roles=("ADMINISTRADOR",))


@pytest.mark.parametrize(("accion", "operacion"), OPERACIONES.items())
def test_las_operaciones_existen_en_el_contrato_del_node_con_el_mismo_identificador(
    accion: str, operacion: str
) -> None:
    contrato = json.loads(CONTRATO_DEL_NODO.read_text(encoding="utf-8"))

    assert contrato["paths"][f"/incidencias/{{codigo}}/{accion}"]["post"]["operationId"] == operacion


def _lector() -> IncidenciasEnMemoria:
    return IncidenciasEnMemoria([un_caso_consultado(estado=EstadoIncidencia.CLASIFICADO)], evidencias=[una_evidencia()])


@pytest.mark.parametrize("accion", ["confirmar", "corregir", "archivar"])
async def test_las_acciones_felices_cumplen_el_contrato_del_node(accion: str) -> None:
    async with un_cliente(un_contenedor(incidencias=_lector()), sesion=ADMIN) as cliente:
        respuesta = await cliente.post(f"{RUTA}/{accion}", json=CUERPOS[accion])

    assert respuesta.status_code == 200
    validar_contrato(openapi_del_nodo(), respuesta)


async def test_corregir_que_saca_el_caso_de_la_vista_cumple_el_contrato_del_node() -> None:
    lector = _lector()
    lector.ocultar_al_cerrar = True
    async with un_cliente(un_contenedor(incidencias=lector), sesion=ADMIN) as cliente:
        a_otro = await cliente.post(f"{RUTA}/corregir", json={"categoria": "otro"})
        lector.casos.append(un_caso_consultado())
        a_denuncia = await cliente.post(f"{RUTA}/corregir", json={"categoria": "denuncia-corrupcion"})

    assert a_otro.json()["caso"] is None
    assert a_denuncia.json()["enviadoAOtrans"] is True
    validar_contrato(openapi_del_nodo(), a_otro)
    validar_contrato(openapi_del_nodo(), a_denuncia)


@pytest.mark.parametrize(
    ("accion", "cuerpo"),
    [
        ("corregir", {}),
        ("derivar", {"descripcionDerivacion": "corta"}),
        ("resolver", {}),
        ("archivar", {"motivo": "VENCIDA_SIN_ATENDER", "detalle": TEXTO}),
        ("reabrir", {"motivo": "corto"}),
    ],
)
async def test_los_cuerpos_invalidos_cumplen_el_contrato_de_errores_del_node(
    accion: str, cuerpo: dict[str, object]
) -> None:
    async with un_cliente(un_contenedor(incidencias=_lector()), sesion=ADMIN) as cliente:
        respuesta = await cliente.post(f"{RUTA}/{accion}", json=cuerpo)

    assert respuesta.status_code == 400
    validar_contrato(openapi_del_nodo(), respuesta)


async def test_los_errores_de_permiso_existencia_y_sesion_cumplen_el_contrato_del_node() -> None:
    contenedor = un_contenedor(incidencias=_lector())
    async with un_cliente(contenedor, sesion=ADMIN) as cliente:
        no_permitida = await cliente.post(f"{RUTA}/tomar")
        no_existe = await cliente.post("/v1/incidencias/MINSA-2026-000099/confirmar")
    async with un_cliente(contenedor, sesion=una_sesion(roles=())) as sin_vistas:
        sin_vista = await sin_vistas.post(f"{RUTA}/confirmar")
    async with un_cliente(contenedor, con_sesion=False) as anonimo:
        sin_sesion = await anonimo.post(f"{RUTA}/confirmar")

    assert [no_permitida.status_code, no_existe.status_code, sin_vista.status_code, sin_sesion.status_code] == [
        403,
        404,
        403,
        401,
    ]
    for respuesta in (no_permitida, no_existe, sin_vista, sin_sesion):
        validar_contrato(openapi_del_nodo(), respuesta)
