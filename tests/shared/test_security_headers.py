from http import HTTPStatus

import pytest

from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.fakes import RaisingPlazoRepository

ORIGEN = "https://app.minsa.gob.pe"
RUTA = "/v1/catalogos/plazos"


class SondaQueFalla:
    async def ping(self) -> bool:
        message = "falla de la sonda"
        raise RuntimeError(message)


CABECERAS_DE_SEGURIDAD = {
    "x-content-type-options": "nosniff",
    "cache-control": "no-store",
    "referrer-policy": "no-referrer",
    "x-frame-options": "DENY",
}


@pytest.mark.parametrize(
    "ruta", ["/salud", RUTA, "/v1/no-existe", "/no-existe"], ids=["salud", "v1", "v1-404", "raiz-404"]
)
async def test_toda_respuesta_lleva_las_cabeceras_de_seguridad(ruta: str) -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get(ruta)

    for nombre, valor in CABECERAS_DE_SEGURIDAD.items():
        assert respuesta.headers[nombre] == valor


@pytest.mark.parametrize("ruta", ["/salud/listo", RUTA], ids=["raiz", "v1"])
async def test_un_error_inesperado_tambien_lleva_las_cabeceras_de_seguridad_y_de_cors(ruta: str) -> None:
    sonda = SondaQueFalla()
    contenedor = un_contenedor(RaisingPlazoRepository(RuntimeError("boom")), sonda=sonda)
    async with un_cliente(contenedor, cors_origins=(ORIGEN,)) as cliente:
        respuesta = await cliente.get(ruta, headers={"Origin": ORIGEN})

    assert respuesta.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert respuesta.json()["errorCode"] == "INTERNAL_ERROR"
    for nombre, valor in CABECERAS_DE_SEGURIDAD.items():
        assert respuesta.headers[nombre] == valor
    assert respuesta.headers["access-control-allow-origin"] == ORIGEN


async def test_la_peticion_previa_de_cors_tambien_lleva_las_cabeceras_de_seguridad() -> None:
    cabeceras = {"Origin": ORIGEN, "Access-Control-Request-Method": "GET"}
    async with un_cliente(un_contenedor(), cors_origins=(ORIGEN,)) as cliente:
        respuesta = await cliente.options(RUTA, headers=cabeceras)

    assert respuesta.status_code == HTTPStatus.OK
    for nombre, valor in CABECERAS_DE_SEGURIDAD.items():
        assert respuesta.headers[nombre] == valor
