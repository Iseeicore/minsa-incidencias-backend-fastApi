from http import HTTPStatus

import pytest

from tests.helpers.app_factory import un_cliente, un_contenedor

RUTAS_DE_DOCUMENTACION = ["/docs", "/redoc", "/openapi.json", "/v1/docs", "/v1/redoc", "/v1/openapi.json"]


@pytest.mark.parametrize("ruta", RUTAS_DE_DOCUMENTACION)
async def test_la_documentacion_interactiva_esta_apagada_por_defecto(ruta: str) -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get(ruta)

    assert respuesta.status_code == HTTPStatus.NOT_FOUND


async def test_la_especificacion_se_sirve_cuando_se_enciende_la_documentacion() -> None:
    async with un_cliente(un_contenedor(), docs_enabled=True) as cliente:
        respuesta = await cliente.get("/v1/openapi.json")

    assert respuesta.status_code == HTTPStatus.OK


async def test_la_especificacion_v1_declara_la_version_del_contrato_y_su_prefijo() -> None:
    async with un_cliente(un_contenedor(), docs_enabled=True) as cliente:
        especificacion = (await cliente.get("/v1/openapi.json")).json()

    assert especificacion["info"]["version"] == "1.0.0"
    assert especificacion["servers"] == [{"url": "/v1"}]
    assert sorted(especificacion["paths"]) == ["/notas", "/notas/{codigo}"]


ORIGEN_PERMITIDO = "https://app.minsa.gob.pe"


async def test_un_origen_permitido_recibe_las_cabeceras_cors_con_credenciales() -> None:
    async with un_cliente(un_contenedor(), cors_origins=(ORIGEN_PERMITIDO,)) as cliente:
        respuesta = await cliente.get("/salud", headers={"Origin": ORIGEN_PERMITIDO})

    assert respuesta.headers["access-control-allow-origin"] == ORIGEN_PERMITIDO
    assert respuesta.headers["access-control-allow-credentials"] == "true"
    assert "Retry-After" in respuesta.headers["access-control-expose-headers"]


async def test_un_origen_no_permitido_no_recibe_cabeceras_cors() -> None:
    async with un_cliente(un_contenedor(), cors_origins=(ORIGEN_PERMITIDO,)) as cliente:
        respuesta = await cliente.get("/salud", headers={"Origin": "https://otro.pe"})

    assert "access-control-allow-origin" not in respuesta.headers


async def test_sin_origenes_configurados_ningun_origen_recibe_cabeceras_cors() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get("/salud", headers={"Origin": ORIGEN_PERMITIDO})

    assert "access-control-allow-origin" not in respuesta.headers


async def test_la_peticion_previa_anuncia_metodos_cabeceras_y_vigencia() -> None:
    cabeceras = {
        "Origin": ORIGEN_PERMITIDO,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    async with un_cliente(un_contenedor(), cors_origins=(ORIGEN_PERMITIDO,)) as cliente:
        respuesta = await cliente.options("/v1/notas", headers=cabeceras)

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.headers["access-control-max-age"] == "600"
    assert set(respuesta.headers["access-control-allow-methods"].split(", ")) == {
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    }
