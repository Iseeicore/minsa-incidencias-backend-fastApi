from http import HTTPStatus

import pytest

from app.catalogos.domain.area_listada import AreaListada, EstablecimientoDeArea
from app.enums.tipo_area import TipoArea
from app.shared.cursor import PosicionPorNombre, encode_int_cursor
from tests.helpers.acceso_en_memoria import AreasEnMemoria
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import una_sesion

RUTA = "/v1/areas"
HOSPITAL = AreaListada(
    10, "HOSP-01", "Hospital Uno", TipoArea.ESTABLECIMIENTO, EstablecimientoDeArea("1234", "II-1", "II-1")
)


async def test_listar_devuelve_la_pagina_con_la_forma_del_contrato() -> None:
    contenedor = un_contenedor(areas=AreasEnMemoria([HOSPITAL]))
    async with un_cliente(contenedor) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == {
        "items": [
            {
                "id": 10,
                "codigo": "HOSP-01",
                "nombre": "Hospital Uno",
                "tipoArea": "ESTABLECIMIENTO",
                "establecimiento": {"codigoRenipress": "1234", "nivelAtencion": "II-1", "categoria": "II-1"},
            }
        ],
        "siguiente": None,
        "hayMas": False,
    }


async def test_los_filtros_llegan_al_caso_de_uso() -> None:
    areas = AreasEnMemoria([HOSPITAL])
    cursor = encode_int_cursor(PosicionPorNombre("Hospital", 3))
    async with un_cliente(un_contenedor(areas=areas), sesion=una_sesion(roles=("ADMINISTRADOR",))) as cliente:
        await cliente.get(RUTA, params={"tipo": "OTRANS", "q": "  hosp ", "limite": 5, "cursor": cursor})

    filtros, limite, despues_de = areas.consultas[0]
    assert (filtros.tipo, filtros.texto, limite) == (TipoArea.OTRANS, "hosp", 6)
    assert despues_de == PosicionPorNombre("Hospital", 3)


async def test_sin_filtros_la_consulta_pide_cincuenta() -> None:
    areas = AreasEnMemoria([])
    async with un_cliente(un_contenedor(areas=areas)) as cliente:
        await cliente.get(RUTA)

    assert areas.consultas[0][1] == 51


@pytest.mark.parametrize(
    ("params", "ruta"),
    [
        ({"tipo": "OTRO"}, "tipo"),
        ({"limite": 0}, "limite"),
        ({"limite": 201}, "limite"),
        ({"q": "x" * 101}, "q"),
        ({"cursor": "x" * 601}, "cursor"),
    ],
)
async def test_parametros_invalidos_responden_400_con_la_ruta_del_campo(
    params: dict[str, str | int], ruta: str
) -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get(RUTA, params=params)

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert [detalle["path"] for detalle in respuesta.json()["details"]] == [ruta]


async def test_un_cursor_alterado_responde_400_con_el_mensaje_del_contrato() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get(RUTA, params={"cursor": "###"})

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["details"] == [{"path": "cursor", "message": "El cursor no es válido."}]


async def test_sin_sesion_responde_401() -> None:
    async with un_cliente(un_contenedor(), con_sesion=False) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
