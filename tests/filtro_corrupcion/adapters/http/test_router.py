from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.shared.sesion import SesionActual
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import una_sesion

RUTA = "/v1/filtro-corrupcion/evaluar"
TEXTO = "La jefa del SIS me pidio plata para atenderme"
GESTOR = una_sesion(roles=("GESTOR",))


def _cliente(sesion: SesionActual = GESTOR, *, con_sesion: bool = True) -> AsyncClient:
    return un_cliente(un_contenedor(), con_sesion=con_sesion, sesion=sesion)


async def test_evalua_el_texto_y_responde_el_resultado_de_las_reglas_sin_combinacion() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post(RUTA, json={"texto": TEXTO})

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert (cuerpo["aplica"], cuerpo["propuestaCorrupcion"], cuerpo["puntaje"], cuerpo["certeza"]) == (
        True,
        True,
        5,
        "ALTA",
    )
    assert cuerpo["versionReglas"] == "reglas-corrupcion-v1.3"
    assert "combinacion" not in cuerpo
    assert cuerpo["referenciaDerivacion"]["codigoEntidad"] == "sis"


@pytest.mark.parametrize("peso", [6, 6.4, None])
async def test_con_pesoia_agrega_la_combinacion_aunque_sea_nulo(peso: float | None) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post(RUTA, json={"texto": TEXTO, "pesoIa": peso})

    combinacion = respuesta.json()["combinacion"]
    assert respuesta.status_code == HTTPStatus.OK
    assert combinacion["pesoIa"] == (None if peso is None else 6)
    assert combinacion["umbral"] == 5


async def test_un_texto_corto_responde_que_no_aplica() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post(RUTA, json={"texto": "muy corto"})

    assert respuesta.json()["aplica"] is False
    assert respuesta.json()["faltantes"] == ["DATOS_INSUFICIENTES"]


async def test_las_entidades_propias_reemplazan_al_catalogo_oficial() -> None:
    cuerpo = {
        "texto": "Me pidieron plata para atenderme en la Clinica Zeta ayer",
        "entidades": [{"codigo": "z", "nombre": "Clinica Zeta"}],
    }
    async with _cliente() as cliente:
        propias = await cliente.post(RUTA, json=cuerpo)
        vacias = await cliente.post(RUTA, json={"texto": TEXTO, "entidades": []})

    assert propias.json()["entidad"]["codigo"] == "z"
    assert vacias.json()["entidad"] is None


@pytest.mark.parametrize(
    ("cuerpo", "ruta"),
    [
        ({}, "texto"),
        ({"texto": 5}, "texto"),
        ({"texto": "x" * 5001}, "texto"),
        ({"texto": TEXTO, "entidades": [{"codigo": "", "nombre": "X"}]}, "entidades.0.codigo"),
        ({"texto": TEXTO, "pesoIa": "6"}, "pesoIa"),
        ({"texto": TEXTO, "establecimientoConocido": "si"}, "establecimientoConocido"),
    ],
)
async def test_un_cuerpo_invalido_responde_400_con_la_ruta_del_campo(cuerpo: dict[str, object], ruta: str) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post(RUTA, json=cuerpo)

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["errorCode"] == "VALIDATION_FAILED"
    assert [detalle["path"] for detalle in respuesta.json()["details"]] == [ruta]


async def test_sin_cuerpo_o_con_cuerpo_nulo_falta_el_texto() -> None:
    async with _cliente() as cliente:
        sin_cuerpo = await cliente.post(RUTA)
        nulo = await cliente.post(RUTA, content=b"null", headers={"Content-Type": "application/json"})

    for respuesta in (sin_cuerpo, nulo):
        assert respuesta.status_code == HTTPStatus.BAD_REQUEST
        assert [detalle["path"] for detalle in respuesta.json()["details"]] == ["texto"]


async def test_un_json_mal_formado_o_que_no_es_un_objeto_responde_400() -> None:
    async with _cliente() as cliente:
        roto = await cliente.post(RUTA, content=b"{no es json", headers={"Content-Type": "application/json"})
        lista = await cliente.post(RUTA, json=[1, 2])

    assert (roto.status_code, lista.status_code) == (HTTPStatus.BAD_REQUEST, HTTPStatus.BAD_REQUEST)


@pytest.mark.parametrize("rol", ["ADMINISTRADOR", "GESTOR", "OTRANS"])
async def test_pueden_probar_el_administrador_el_gestor_y_otrans(rol: str) -> None:
    async with _cliente(una_sesion(roles=(rol,))) as cliente:
        respuesta = await cliente.post(RUTA, json={"texto": TEXTO})

    assert respuesta.status_code == HTTPStatus.OK


@pytest.mark.parametrize("roles", [("ESTABLECIMIENTO",), ()])
async def test_los_demas_roles_reciben_403_antes_de_validar_el_cuerpo(roles: tuple[str, ...]) -> None:
    async with _cliente(una_sesion(roles=roles)) as cliente:
        respuesta = await cliente.post(RUTA, json={})

    assert respuesta.status_code == HTTPStatus.FORBIDDEN


async def test_sin_sesion_responde_401() -> None:
    async with _cliente(con_sesion=False) as cliente:
        respuesta = await cliente.post(RUTA, json={"texto": TEXTO})

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
