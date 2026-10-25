from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.domain.caso_consultado import ConteoPorVencer
from app.incidencias.domain.cursores import PosicionDeListado, codificar_cursor
from app.shared.sesion import SesionActual
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_caso_consultado, una_evidencia, una_sesion
from tests.helpers.casos import IMAGEN_PNG
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

RUTA = "/v1/incidencias"
CODIGO = "MINSA-2026-000001"
EVIDENCIA = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"
ADMIN = una_sesion(roles=("ADMINISTRADOR",))
SIN_VISTAS = una_sesion(roles=())


def _cliente(
    lector: IncidenciasEnMemoria | None = None, sesion: SesionActual = ADMIN, *, con_sesion: bool = True
) -> AsyncClient:
    contenedor = un_contenedor(incidencias=lector or IncidenciasEnMemoria([un_caso_consultado()]))
    return un_cliente(contenedor, con_sesion=con_sesion, sesion=sesion)


async def test_listar_devuelve_la_pagina_con_los_casos_y_sus_acciones() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(RUTA)

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert (cuerpo["siguiente"], cuerpo["hayMas"]) == (None, False)
    assert cuerpo["items"][0]["codigo"] == CODIGO
    assert cuerpo["items"][0]["acciones"] == ["confirmar", "corregir", "archivar"]


async def test_listar_pasa_los_filtros_y_el_limite_al_lector() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()])
    parametros: dict[str, str | int] = {
        "estado": "clasificado",
        "motivoArchivo": "NO_CORRESPONDE",
        "categoria": "sin-categoria",
        "texto": "  goteras ",
        "establecimiento": "00001234",
        "desde": "2026-01-01",
        "hasta": "2026-01-31",
        "limite": 5,
    }
    async with _cliente(lector) as cliente:
        respuesta = await cliente.get(RUTA, params=parametros)

    filtros = lector.llamadas[0][1][1]
    assert respuesta.status_code == HTTPStatus.OK
    assert (filtros.estado, filtros.sin_categoria, filtros.texto, filtros.establecimiento) == (
        EstadoIncidencia.CLASIFICADO,
        True,
        "goteras",
        "1234",
    )
    assert (filtros.desde, filtros.hasta, filtros.motivo_archivo.value) == (
        "2026-01-01",
        "2026-01-31",
        "NO_CORRESPONDE",
    )
    assert lector.llamadas[0][1][2] == 6


async def test_listar_con_cursor_continua_desde_esa_posicion() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()])
    posicion = PosicionDeListado(un_caso_consultado().fecha_creacion, "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69")
    async with _cliente(lector) as cliente:
        await cliente.get(RUTA, params={"cursor": codificar_cursor(posicion)})

    assert lector.llamadas[0][1][3] == posicion


@pytest.mark.parametrize(
    ("parametros", "ruta"),
    [
        ({"estado": "otro"}, "estado"),
        ({"categoria": "x"}, "categoria"),
        ({"plazo": "vencido"}, "plazo"),
        ({"limite": 0}, "limite"),
        ({"limite": 101}, "limite"),
        ({"texto": "x" * 101}, "texto"),
        ({"cursor": "x" * 201}, "cursor"),
        ({"desde": "2026-02-30"}, "desde"),
        ({"establecimiento": "abc"}, "establecimiento"),
        ({"cursor": "###"}, "cursor"),
    ],
)
async def test_parametros_invalidos_responden_400_con_la_ruta_del_campo(
    parametros: dict[str, str | int], ruta: str
) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(RUTA, params=parametros)

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert [detalle["path"] for detalle in respuesta.json()["details"]] == [ruta]


async def test_sin_sesion_responde_401_y_sin_la_vista_de_casos_403() -> None:
    async with _cliente(con_sesion=False) as anonimo:
        sin_sesion = await anonimo.get(RUTA)
    async with _cliente(sesion=SIN_VISTAS) as cliente:
        prohibido = await cliente.get(RUTA)
        conteos = await cliente.get(f"{RUTA}/conteos")
        detalle = await cliente.get(f"{RUTA}/{CODIGO}")

    assert sin_sesion.status_code == HTTPStatus.UNAUTHORIZED
    assert {prohibido.status_code, conteos.status_code, detalle.status_code} == {HTTPStatus.FORBIDDEN}


async def test_conteos_devuelve_los_totales_por_estado() -> None:
    lector = IncidenciasEnMemoria()
    lector.por_estado = {EstadoIncidencia.CLASIFICADO: 4}
    async with _cliente(lector) as cliente:
        respuesta = await cliente.get(f"{RUTA}/conteos", params={"estado": "clasificado"})

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert cuerpo["todos"] == {"cantidad": 4, "conMas": False}
    assert cuerpo["porEstado"]["clasificado"] == {"cantidad": 4, "conMas": False}


async def test_conteos_valida_los_filtros_pero_ignora_el_limite_y_el_cursor() -> None:
    async with _cliente() as cliente:
        invalido = await cliente.get(f"{RUTA}/conteos", params={"desde": "x"})
        con_limite = await cliente.get(f"{RUTA}/conteos", params={"limite": 500, "cursor": "###"})

    assert invalido.status_code == HTTPStatus.BAD_REQUEST
    assert con_limite.status_code == HTTPStatus.OK


async def test_por_vencer_solo_exige_sesion() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()])
    lector.conteo_por_vencer = ConteoPorVencer(total=2, vencidos=1)
    async with _cliente(lector, sesion=SIN_VISTAS) as cliente:
        respuesta = await cliente.get(f"{RUTA}/por-vencer")
    async with _cliente(lector, con_sesion=False) as anonimo:
        sin_sesion = await anonimo.get(f"{RUTA}/por-vencer")

    assert respuesta.status_code == HTTPStatus.OK
    assert (respuesta.json()["total"], respuesta.json()["porVencer"], respuesta.json()["vencidos"]) == (2, 1, 1)
    assert sin_sesion.status_code == HTTPStatus.UNAUTHORIZED


async def test_detalle_devuelve_el_caso_con_sus_evidencias() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()], evidencias=[una_evidencia()])
    async with _cliente(lector) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{CODIGO}")

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert cuerpo["codigo"] == CODIGO
    assert cuerpo["evidencias"][0]["id"] == "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"
    assert cuerpo["descripcion"] == "Relato del caso."


@pytest.mark.parametrize("codigo", ["conteo", "MINSA-2026-1", "no-es-un-codigo", "MINSA-2026-000099"])
async def test_detalle_de_un_caso_que_no_existe_o_con_otro_formato_responde_404(codigo: str) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(f"{RUTA}/{codigo}")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["errorCode"] == "NOT_FOUND"


async def test_el_contenido_de_una_evidencia_se_entrega_como_imagen_con_cabeceras_estrictas() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()], rutas={EVIDENCIA: IMAGEN_PNG})
    async with _cliente(lector) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{CODIGO}/evidencias/{EVIDENCIA}/contenido")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.content.startswith(b"\x89PNG")
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.headers["content-length"] == str(len(respuesta.content))
    assert respuesta.headers["cache-control"] == "private, no-store"
    assert respuesta.headers["content-disposition"] == "inline"
    assert respuesta.headers["content-security-policy"] == "default-src 'none'; sandbox"
    assert respuesta.headers["x-content-type-options"] == "nosniff"


async def test_una_evidencia_que_no_es_imagen_responde_evidencia_no_disponible() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()], rutas={EVIDENCIA: "rutas-privadas/archivo.jpg"})
    async with _cliente(lector) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{CODIGO}/evidencias/{EVIDENCIA}/contenido")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["errorCode"] == "EVIDENCIA_NO_DISPONIBLE"


@pytest.mark.parametrize("evidencia", [EVIDENCIA, "no-es-uuid", EVIDENCIA.upper()])
async def test_una_evidencia_inexistente_o_con_id_invalido_responde_404_con_su_mensaje(evidencia: str) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(f"{RUTA}/{CODIGO}/evidencias/{evidencia}/contenido")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["message"] == "La evidencia solicitada no existe."
