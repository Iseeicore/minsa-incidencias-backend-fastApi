from http import HTTPStatus

import pytest

from app.errors.database_timeout import DatabaseTimeout
from app.errors.database_unavailable import DatabaseUnavailable
from app.nota.domain.constantes import CONTENIDO_MAX_LENGTH, TITULO_MAX_LENGTH
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import una_nota
from tests.helpers.fakes import InMemoryNotaRepository, RaisingNotaRepository

CUERPO_VALIDO = {"titulo": "Titulo", "contenido": "Contenido"}


async def test_crea_una_nota_y_devuelve_su_ubicacion() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.post("/v1/notas", json=CUERPO_VALIDO)

    assert respuesta.status_code == HTTPStatus.CREATED
    assert respuesta.headers["location"] == "/v1/notas/NOTA-000001"
    assert respuesta.json() == {
        "codigo": "NOTA-000001",
        "titulo": "Titulo",
        "contenido": "Contenido",
        "creadaEn": "2026-10-24T12:00:00Z",
    }


async def test_consulta_una_nota_que_existe() -> None:
    contenedor = un_contenedor(InMemoryNotaRepository([una_nota(3, titulo="Guardada")]))

    async with un_cliente(contenedor) as cliente:
        respuesta = await cliente.get("/v1/notas/NOTA-000003")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()["titulo"] == "Guardada"


async def test_una_nota_inexistente_responde_404_con_el_formato_unico() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get("/v1/notas/NOTA-000099")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json() == {
        "statusCode": 404,
        "errorCode": "NOTA_NOT_FOUND",
        "message": "La nota no existe",
        "timestamp": "2026-10-24T12:00:00Z",
        "path": "/v1/notas/NOTA-000099",
        "details": {"codigo": "NOTA-000099"},
    }


async def test_un_codigo_con_otro_formato_responde_422() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get("/v1/notas/otro")

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert respuesta.json()["errorCode"] == "NOTA_CODIGO_INVALID"


async def test_un_titulo_vacio_responde_422_por_regla_de_negocio() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.post("/v1/notas", json={"titulo": " ", "contenido": "Contenido"})

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert respuesta.json()["errorCode"] == "NOTA_TITULO_INVALID"


async def test_un_cuerpo_sin_campos_responde_422_con_el_formato_unico() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.post("/v1/notas", json={"titulo": "Titulo"})

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert cuerpo["errorCode"] == "REQUEST_INVALID"
    assert cuerpo["path"] == "/v1/notas"
    assert cuerpo["details"]


async def test_un_titulo_mas_largo_que_el_maximo_responde_422_en_la_frontera() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.post("/v1/notas", json={"titulo": "x" * (TITULO_MAX_LENGTH + 1), "contenido": "c"})

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert respuesta.json()["errorCode"] == "REQUEST_INVALID"
    assert respuesta.json()["details"][0]["path"] == "body.titulo"


async def test_un_contenido_mas_largo_que_el_maximo_responde_422_en_la_frontera() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.post("/v1/notas", json={"titulo": "t", "contenido": "x" * (CONTENIDO_MAX_LENGTH + 1)})

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert respuesta.json()["details"][0]["path"] == "body.contenido"


async def test_un_campo_desconocido_en_el_cuerpo_responde_422() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.post("/v1/notas", json={**CUERPO_VALIDO, "extra": "no permitido"})

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert respuesta.json()["details"][0]["path"] == "body.extra"


async def test_un_codigo_de_ruta_demasiado_largo_responde_422_sin_repetir_el_valor() -> None:
    codigo = "NOTA-" + "9" * 200
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get(f"/v1/notas/{codigo}")

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert respuesta.json()["errorCode"] == "REQUEST_INVALID"
    assert codigo not in str(respuesta.json()["details"])


@pytest.mark.parametrize(
    ("error", "estado", "codigo"),
    [
        (DatabaseUnavailable(), HTTPStatus.SERVICE_UNAVAILABLE, "DATABASE_UNAVAILABLE"),
        (DatabaseTimeout(), HTTPStatus.GATEWAY_TIMEOUT, "DATABASE_TIMEOUT"),
    ],
    ids=["no-disponible", "tiempo-agotado"],
)
async def test_los_fallos_de_la_base_responden_503_o_504_con_el_formato_unico(
    error: Exception, estado: HTTPStatus, codigo: str
) -> None:
    async with un_cliente(un_contenedor(RaisingNotaRepository(error))) as cliente:
        consulta = await cliente.get("/v1/notas/NOTA-000001")
        creacion = await cliente.post("/v1/notas", json=CUERPO_VALIDO)

    assert consulta.status_code == creacion.status_code == estado
    assert consulta.json()["errorCode"] == creacion.json()["errorCode"] == codigo
