from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.shared.sesion import SesionActual
from tests.helpers.analisis_en_memoria import AnalisisEnMemoria, una_fila_de_analisis
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_caso_consultado, una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

CODIGO = "MINSA-2026-000001"
ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUTAS = [f"/v1/incidencias/{CODIGO}/clasificacion", f"/v1/incidencias/{CODIGO}/analisis-ia"]
OTRANS = una_sesion(roles=("OTRANS",))


def _cliente(
    analisis: AnalisisEnMemoria | None = None,
    casos: IncidenciasEnMemoria | None = None,
    sesion: SesionActual = OTRANS,
    *,
    con_sesion: bool = True,
) -> AsyncClient:
    contenedor = un_contenedor(
        incidencias=casos or IncidenciasEnMemoria([un_caso_consultado()]),
        analisis=analisis or AnalisisEnMemoria({ID: una_fila_de_analisis()}),
    )
    return un_cliente(contenedor, con_sesion=con_sesion, sesion=sesion)


@pytest.mark.parametrize("ruta", RUTAS)
async def test_la_clasificacion_y_su_alias_devuelven_el_mismo_analisis(ruta: str) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(ruta)

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert (cuerpo["codigo"], cuerpo["versionReglas"], cuerpo["puntaje"]) == (CODIGO, "reglas-corrupcion-v1.3", 5)
    assert cuerpo["etiquetaNormas"] == "Referencia orientativa; la califica OTRANS."


@pytest.mark.parametrize("ruta", RUTAS)
async def test_un_caso_sin_analisis_responde_404_con_su_mensaje(ruta: str) -> None:
    async with _cliente(AnalisisEnMemoria({"otro": una_fila_de_analisis()})) as cliente:
        respuesta = await cliente.get(ruta)

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["message"] == "El caso todavía no tiene análisis de clasificación."


@pytest.mark.parametrize("ruta", RUTAS)
async def test_un_caso_que_no_se_ve_responde_404_con_el_mensaje_del_caso(ruta: str) -> None:
    async with _cliente(casos=IncidenciasEnMemoria()) as cliente:
        respuesta = await cliente.get(ruta)

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["message"] == "El caso solicitado no existe."


@pytest.mark.parametrize("sufijo", ["clasificacion", "analisis-ia"])
async def test_un_codigo_con_forma_invalida_responde_404(sufijo: str) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(f"/v1/incidencias/no-es-un-codigo/{sufijo}")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize("roles", [("GESTOR",), ("ESTABLECIMIENTO",), ()])
async def test_solo_otrans_y_el_administrador_pueden_leerlo(roles: tuple[str, ...]) -> None:
    async with _cliente(sesion=una_sesion(roles=roles)) as cliente:
        respuestas = [await cliente.get(ruta) for ruta in RUTAS]

    assert {respuesta.status_code for respuesta in respuestas} == {HTTPStatus.FORBIDDEN}


async def test_el_administrador_tambien_puede_leerlo() -> None:
    async with _cliente(sesion=una_sesion(roles=("ADMINISTRADOR",))) as cliente:
        respuesta = await cliente.get(RUTAS[0])

    assert respuesta.status_code == HTTPStatus.OK


async def test_sin_sesion_responde_401() -> None:
    async with _cliente(con_sesion=False) as cliente:
        respuesta = await cliente.get(RUTAS[0])

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
