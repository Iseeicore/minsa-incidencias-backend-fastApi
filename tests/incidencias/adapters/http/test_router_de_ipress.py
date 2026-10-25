from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.domain.consultas import VisibilidadDeIpress
from app.incidencias.domain.ipress import IpressConsultada, IpressListada
from app.shared.cursor import PosicionPorNombre, encode_int_cursor
from app.shared.sesion import SesionActual
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_caso_consultado, una_evidencia, una_sesion
from tests.helpers.casos import IMAGEN_PNG
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria
from tests.helpers.indicadores_en_memoria import IndicadoresEnMemoria, IpressEnMemoria

RUTA = "/v1/consulta-ipress"
RENIPRESS = "1234"
CODIGO = "MINSA-2026-000001"
EVIDENCIA = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"
OTRANS = una_sesion(roles=("OTRANS",))
VISIBLE = VisibilidadDeIpress(establecimiento_id=7)
NO_DISPONIBLE = "El establecimiento no está disponible."


def _cliente(
    casos: IncidenciasEnMemoria | None = None,
    ipress: IpressEnMemoria | None = None,
    indicadores: IndicadoresEnMemoria | None = None,
    sesion: SesionActual = OTRANS,
    *,
    con_sesion: bool = True,
) -> AsyncClient:
    contenedor = un_contenedor(
        incidencias=casos or IncidenciasEnMemoria([un_caso_consultado()], evidencias=[una_evidencia()]),
        ipress=ipress or IpressEnMemoria({RENIPRESS: IpressConsultada(7, "EESS-0001", "Centro de Salud")}),
        indicadores=indicadores or IndicadoresEnMemoria(),
    )
    return un_cliente(contenedor, con_sesion=con_sesion, sesion=sesion)


async def test_buscar_ipress_devuelve_la_pagina_con_el_formato_de_las_areas() -> None:
    ipress = IpressEnMemoria(listadas=[IpressListada(3, "EESS-0001", "Centro de Salud", "1", "I", "I-3")])
    async with _cliente(ipress=ipress) as cliente:
        respuesta = await cliente.get(f"{RUTA}/establecimientos", params={"q": " centro ", "limite": 5})

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()["items"][0]["tipoArea"] == "ESTABLECIMIENTO"
    consulta, limite = ipress.consultas[0]
    assert (consulta.texto, limite) == ("centro", 6)


async def test_buscar_ipress_continua_desde_el_cursor() -> None:
    ipress = IpressEnMemoria()
    posicion = PosicionPorNombre("Centro", 4)
    async with _cliente(ipress=ipress) as cliente:
        await cliente.get(f"{RUTA}/establecimientos", params={"cursor": encode_int_cursor(posicion)})

    assert ipress.consultas[0][0].despues_de == posicion


@pytest.mark.parametrize(
    ("parametros", "ruta"),
    [({"limite": 0}, "limite"), ({"limite": 201}, "limite"), ({"q": "x" * 101}, "q"), ({"cursor": "###"}, "cursor")],
)
async def test_buscar_ipress_con_parametros_invalidos_responde_400(parametros: dict[str, str | int], ruta: str) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(f"{RUTA}/establecimientos", params=parametros)

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert [detalle["path"] for detalle in respuesta.json()["details"]] == [ruta]


async def test_el_resumen_devuelve_los_conteos_generales() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(f"{RUTA}/{RENIPRESS}/resumen")

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert (cuerpo["total"], cuerpo["enGestion"], len(cuerpo["porCategoria"])) == (0, 0, 5)


async def test_los_indicadores_llevan_el_alcance_de_la_ipress_y_el_periodo_pedido() -> None:
    indicadores = IndicadoresEnMemoria()
    async with _cliente(indicadores=indicadores) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{RENIPRESS}/indicadores", params={"periodo": "30d"})

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert cuerpo["periodo"] == "30d"
    assert cuerpo["alcance"]["area"]["codigo"] == "EESS-0001"
    assert indicadores.llamadas[0][1][:2] == (VISIBLE, 30)


async def test_los_ceros_a_la_izquierda_del_codigo_renipress_se_ignoran() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(f"{RUTA}/00001234/resumen")

    assert respuesta.status_code == HTTPStatus.OK


@pytest.mark.parametrize("renipress", ["abc", "123456789", "0", "9999"])
async def test_un_codigo_renipress_invalido_o_desconocido_responde_404_con_el_mensaje_del_establecimiento(
    renipress: str,
) -> None:
    async with _cliente() as cliente:
        rutas = [
            f"{RUTA}/{renipress}/resumen",
            f"{RUTA}/{renipress}/indicadores",
            f"{RUTA}/{renipress}/incidencias",
            f"{RUTA}/{renipress}/conteos",
            f"{RUTA}/{renipress}/incidencias/{CODIGO}",
            f"{RUTA}/{renipress}/incidencias/{CODIGO}/evidencias/{EVIDENCIA}/contenido",
        ]
        respuestas = [await cliente.get(ruta) for ruta in rutas]

    assert {respuesta.status_code for respuesta in respuestas} == {HTTPStatus.NOT_FOUND}
    assert {respuesta.json()["message"] for respuesta in respuestas} == {NO_DISPONIBLE}


async def test_la_validacion_de_la_consulta_va_antes_que_la_busqueda_de_la_ipress() -> None:
    async with _cliente() as cliente:
        indicadores = await cliente.get(f"{RUTA}/abc/indicadores", params={"periodo": "15d"})
        listado = await cliente.get(f"{RUTA}/abc/incidencias", params={"limite": 0})

    assert (indicadores.status_code, listado.status_code) == (HTTPStatus.BAD_REQUEST, HTTPStatus.BAD_REQUEST)


async def test_el_listado_usa_diez_por_defecto_ignora_el_establecimiento_y_no_trae_acciones() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()])
    async with _cliente(casos) as cliente:
        respuesta = await cliente.get(
            f"{RUTA}/{RENIPRESS}/incidencias", params={"establecimiento": "999", "texto": "x"}
        )

    nombre, argumentos = casos.llamadas[0]
    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()["items"][0]["acciones"] == []
    assert (nombre, argumentos[0], argumentos[2]) == ("listar", VISIBLE, 11)
    assert (argumentos[1].establecimiento, argumentos[1].texto) == (None, "x")


async def test_el_listado_valida_el_establecimiento_aunque_lo_ignore() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(f"{RUTA}/{RENIPRESS}/incidencias", params={"establecimiento": "abc"})

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert [detalle["path"] for detalle in respuesta.json()["details"]] == ["establecimiento"]


async def test_los_conteos_se_acotan_a_la_ipress() -> None:
    casos = IncidenciasEnMemoria()
    casos.por_estado = {EstadoIncidencia.CLASIFICADO: 3}
    async with _cliente(casos) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{RENIPRESS}/conteos", params={"establecimiento": "999"})

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()["porEstado"]["clasificado"] == {"cantidad": 3, "conMas": False}
    assert all(argumentos[0] == VISIBLE for _, argumentos in casos.llamadas)


async def test_el_detalle_del_caso_sale_sin_acciones() -> None:
    async with _cliente(sesion=una_sesion(roles=("ADMINISTRADOR",))) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{RENIPRESS}/incidencias/{CODIGO}")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()["codigo"] == CODIGO
    assert respuesta.json()["acciones"] == []


async def test_un_codigo_de_caso_invalido_responde_404_antes_de_buscar_la_ipress() -> None:
    async with _cliente(ipress=IpressEnMemoria()) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{RENIPRESS}/incidencias/no-es-un-codigo")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["message"] != NO_DISPONIBLE


async def test_la_evidencia_se_entrega_con_las_cabeceras_de_imagen() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()], rutas={EVIDENCIA: IMAGEN_PNG})
    async with _cliente(casos) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{RENIPRESS}/incidencias/{CODIGO}/evidencias/{EVIDENCIA}/contenido")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize(
    "sesion", [una_sesion(roles=("GESTOR",)), una_sesion(roles=("ESTABLECIMIENTO",)), una_sesion(roles=())]
)
async def test_sin_la_vista_o_sin_el_rol_responde_403(sesion: SesionActual) -> None:
    async with _cliente(sesion=sesion) as cliente:
        respuestas = [
            await cliente.get(f"{RUTA}/establecimientos"),
            await cliente.get(f"{RUTA}/{RENIPRESS}/resumen"),
            await cliente.get(f"{RUTA}/{RENIPRESS}/incidencias/{CODIGO}"),
        ]

    assert {respuesta.status_code for respuesta in respuestas} == {HTTPStatus.FORBIDDEN}


async def test_sin_sesion_responde_401() -> None:
    async with _cliente(con_sesion=False) as cliente:
        respuesta = await cliente.get(f"{RUTA}/establecimientos")

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
