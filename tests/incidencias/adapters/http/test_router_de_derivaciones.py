from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.incidencias.domain.cursores import PosicionDeDerivacion, codificar_cursor_de_derivacion
from app.incidencias.domain.derivaciones import ConteosDeDerivaciones
from app.shared.sesion import SesionActual
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_caso_consultado, una_derivacion_consultada, una_evidencia, una_sesion
from tests.helpers.casos import IMAGEN_PNG
from tests.helpers.derivaciones_en_memoria import DerivacionesEnMemoria
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

RUTA = "/v1/derivaciones"
CODIGO = "MINSA-2026-000001"
EVIDENCIA = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"
OTRANS = una_sesion(roles=("OTRANS",))
ADMIN = una_sesion(roles=("ADMINISTRADOR",))


def _cliente(
    envios: DerivacionesEnMemoria | None = None,
    casos: IncidenciasEnMemoria | None = None,
    sesion: SesionActual = OTRANS,
    *,
    con_sesion: bool = True,
) -> AsyncClient:
    contenedor = un_contenedor(
        derivaciones=envios or DerivacionesEnMemoria([una_derivacion_consultada()]),
        incidencias=casos or IncidenciasEnMemoria([un_caso_consultado()], evidencias=[una_evidencia()]),
    )
    return un_cliente(contenedor, con_sesion=con_sesion, sesion=sesion)


async def test_listar_devuelve_la_pagina_de_derivaciones() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(RUTA)

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert (cuerpo["siguiente"], cuerpo["hayMas"]) == (None, False)
    assert cuerpo["items"][0]["codigoCaso"] == CODIGO
    assert cuerpo["items"][0]["derivadoPor"] == "Lucía Ramos"


async def test_listar_pasa_los_filtros_el_limite_y_el_cursor_al_lector() -> None:
    envios = DerivacionesEnMemoria([una_derivacion_consultada()])
    posicion = PosicionDeDerivacion(una_derivacion_consultada().fecha_derivacion.replace(microsecond=0), "4821")
    parametros: dict[str, str | int] = {
        "situacion": "pendiente",
        "texto": " 000001 ",
        "establecimiento": "00001234",
        "categoria": "reclamo",
        "desde": "2026-01-01",
        "hasta": "2026-01-31",
        "limite": 5,
        "cursor": codificar_cursor_de_derivacion(posicion),
    }
    async with _cliente(envios) as cliente:
        respuesta = await cliente.get(RUTA, params=parametros)

    consulta, limite = envios.consultas[0]
    assert respuesta.status_code == HTTPStatus.OK
    assert limite == 6
    assert (consulta.filtros.situacion, consulta.filtros.texto, consulta.filtros.establecimiento) == (
        "pendiente",
        "000001",
        "1234",
    )
    assert consulta.despues_de == posicion


@pytest.mark.parametrize(
    ("parametros", "ruta"),
    [
        ({"situacion": "otra"}, "situacion"),
        ({"categoria": "sin-categoria"}, "categoria"),
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


async def test_conteos_devuelve_los_totales_y_valida_pero_no_aplica_la_situacion() -> None:
    envios = DerivacionesEnMemoria()
    envios.conteos = ConteosDeDerivaciones(4, 1, 1, 1, 1)
    async with _cliente(envios) as cliente:
        respuesta = await cliente.get(f"{RUTA}/conteos", params={"situacion": "resuelto", "texto": "1"})

    assert respuesta.json() == {"todos": 4, "pendientes": 1, "enGestion": 1, "resueltos": 1, "archivados": 1}
    assert envios.filtros_contados[0].situacion is None
    assert envios.filtros_contados[0].texto == "1"


async def test_conteos_con_un_filtro_invalido_responde_400() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(f"{RUTA}/conteos", params={"situacion": "otra"})

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST


async def test_detalle_une_el_envio_y_el_caso_sin_acciones() -> None:
    async with _cliente(sesion=ADMIN) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{CODIGO}")

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert cuerpo["derivacion"]["id"] == "4821"
    assert cuerpo["caso"]["codigo"] == CODIGO
    assert cuerpo["caso"]["acciones"] == []


async def test_detalle_de_un_caso_sin_envio_responde_404_con_el_mensaje_de_la_derivacion() -> None:
    async with _cliente(DerivacionesEnMemoria()) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{CODIGO}")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["message"] == "La derivación no está disponible."


async def test_un_codigo_con_forma_invalida_responde_404() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(f"{RUTA}/no-es-un-codigo")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND


async def test_la_evidencia_se_entrega_con_las_cabeceras_de_imagen() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()], rutas={EVIDENCIA: IMAGEN_PNG})
    async with _cliente(casos=casos) as cliente:
        respuesta = await cliente.get(f"{RUTA}/{CODIGO}/evidencias/{EVIDENCIA}/contenido")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.headers["cache-control"] == "private, no-store"
    assert respuesta.headers["content-length"] == str(len(respuesta.content))


async def test_una_evidencia_con_id_invalido_responde_404_con_el_mensaje_de_la_evidencia() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(f"{RUTA}/{CODIGO}/evidencias/no-es-uuid/contenido")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["message"] == "La evidencia solicitada no existe."


@pytest.mark.parametrize(
    "sesion", [una_sesion(roles=("GESTOR",)), una_sesion(roles=("ESTABLECIMIENTO",)), una_sesion(roles=())]
)
async def test_sin_la_vista_o_sin_el_rol_responde_403(sesion: SesionActual) -> None:
    async with _cliente(sesion=sesion) as cliente:
        respuestas = [
            await cliente.get(RUTA),
            await cliente.get(f"{RUTA}/conteos"),
            await cliente.get(f"{RUTA}/{CODIGO}"),
            await cliente.get(f"{RUTA}/{CODIGO}/evidencias/{EVIDENCIA}/contenido"),
        ]

    assert {respuesta.status_code for respuesta in respuestas} == {HTTPStatus.FORBIDDEN}


async def test_sin_sesion_responde_401() -> None:
    async with _cliente(con_sesion=False) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
