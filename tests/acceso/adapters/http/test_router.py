from http import HTTPStatus
from typing import Any

import pytest

from app.composition import Container
from app.shared.session_cookie import clear_cookie_header, read_session_id
from tests.helpers.acceso_en_memoria import SesionesDeAccesoEnMemoria, UsuariosDeAccesoEnMemoria
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import (
    cabecera_de_cookie,
    un_usuario_interno,
    una_config_de_cookie,
    una_politica,
    una_seguridad,
    una_sesion,
    una_sesion_vigente,
)
from tests.helpers.fakes import SesionesEnMemoria

LOGIN = "/v1/auth/login"
LOGOUT = "/v1/auth/logout"
ME = "/v1/auth/me"
CREDENCIALES = {"correo": "gestor@minsa.gob.pe", "password": "clave-correcta"}


def _contenedor_con_usuario(**extras: Any) -> Container:  # noqa: ANN401
    return un_contenedor(usuarios_de_acceso=UsuariosDeAccesoEnMemoria([un_usuario_interno()]), **extras)


async def test_el_login_correcto_responde_204_con_la_cookie_de_sesion_firmada() -> None:
    sesiones = SesionesDeAccesoEnMemoria()
    async with un_cliente(_contenedor_con_usuario(sesiones_de_acceso=sesiones), con_sesion=False) as cliente:
        respuesta = await cliente.post(LOGIN, json=CREDENCIALES)

    cookie = respuesta.headers["set-cookie"]
    valor = cookie.split(";")[0].split("=", 1)[1]
    assert respuesta.status_code == HTTPStatus.NO_CONTENT
    assert respuesta.content == b""
    assert read_session_id({"gestion_sid": valor}, una_config_de_cookie()) is not None
    assert "Max-Age=28800" in cookie
    assert "Expires=Sat, 24 Oct 2026 20:00:00 GMT" in cookie
    assert cookie.endswith("HttpOnly; SameSite=Strict")
    assert sesiones.creadas == [("usuario:gestor@minsa.gob.pe", un_usuario_interno().id, 8)]


async def test_el_login_informa_el_limite_restante_de_su_cubeta() -> None:
    async with un_cliente(_contenedor_con_usuario(), con_sesion=False) as cliente:
        respuesta = await cliente.post(LOGIN, json=CREDENCIALES)

    assert respuesta.headers["ratelimit-limit"] == "1000"


async def test_unas_credenciales_incorrectas_responden_401_invalid_credentials() -> None:
    async with un_cliente(_contenedor_con_usuario(), con_sesion=False) as cliente:
        respuesta = await cliente.post(LOGIN, json={**CREDENCIALES, "password": "otra"})

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()["errorCode"] == "INVALID_CREDENTIALS"
    assert respuesta.json()["message"] == "Correo o contraseña incorrectos."
    assert "set-cookie" not in respuesta.headers


@pytest.mark.parametrize(
    ("cuerpo", "ruta"),
    [
        ({"correo": "no-es-correo", "password": "x"}, "correo"),
        ({"correo": "a@minsa.gob.pe"}, "password"),
        ({}, "correo"),
    ],
)
async def test_un_cuerpo_invalido_responde_400_con_la_ruta_del_campo(cuerpo: dict[str, str], ruta: str) -> None:
    async with un_cliente(_contenedor_con_usuario(), con_sesion=False) as cliente:
        respuesta = await cliente.post(LOGIN, json=cuerpo)

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["errorCode"] == "VALIDATION_FAILED"
    assert ruta in {detalle["path"] for detalle in respuesta.json()["details"]}


async def test_iniciar_sesion_estando_en_una_revoca_la_anterior() -> None:
    anterior = una_sesion()
    sesiones = SesionesDeAccesoEnMemoria()
    contenedor = _contenedor_con_usuario(
        sesiones_de_acceso=sesiones, resolvedor=SesionesEnMemoria({anterior.sesion_id: anterior})
    )
    async with un_cliente(contenedor, con_sesion=False) as cliente:
        respuesta = await cliente.post(LOGIN, json=CREDENCIALES, headers=cabecera_de_cookie(anterior.sesion_id))

    assert respuesta.status_code == HTTPStatus.NO_CONTENT
    assert sesiones.revocadas == [(f"usuario:{anterior.correo}", anterior.sesion_id)]


async def test_el_sexto_intento_por_correo_responde_429() -> None:
    seguridad = una_seguridad(login_por_correo=una_politica(5), login_por_ip=una_politica(30))
    async with un_cliente(_contenedor_con_usuario(seguridad=seguridad), con_sesion=False) as cliente:
        for _ in range(5):
            await cliente.post(LOGIN, json={**CREDENCIALES, "password": "mal"})
        respuesta = await cliente.post(LOGIN, json=CREDENCIALES)

    assert respuesta.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert respuesta.json()["errorCode"] == "RATE_LIMITED"
    assert "retry-after" in respuesta.headers


async def test_el_cierre_de_sesion_borra_la_cookie_y_revoca_la_sesion() -> None:
    vigente = una_sesion_vigente()
    sesiones = SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente})
    async with un_cliente(_contenedor_con_usuario(sesiones_de_acceso=sesiones), con_sesion=False) as cliente:
        respuesta = await cliente.post(LOGOUT, headers=cabecera_de_cookie(vigente.sesion_id))

    assert respuesta.status_code == HTTPStatus.NO_CONTENT
    assert respuesta.headers["set-cookie"] == clear_cookie_header(una_config_de_cookie())
    assert sesiones.revocadas == [(f"usuario:{vigente.correo}", vigente.sesion_id)]


async def test_el_cierre_de_sesion_sin_cookie_responde_204_y_borra_la_cookie() -> None:
    async with un_cliente(_contenedor_con_usuario(), con_sesion=False) as cliente:
        respuesta = await cliente.post(LOGOUT)

    assert respuesta.status_code == HTTPStatus.NO_CONTENT
    assert respuesta.headers["set-cookie"] == clear_cookie_header(una_config_de_cookie())


async def test_si_la_revocacion_falla_el_cierre_responde_204_igual() -> None:
    vigente = una_sesion_vigente()
    sesiones = SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente})
    sesiones.falla_al_revocar = RuntimeError("base caída")
    async with un_cliente(_contenedor_con_usuario(sesiones_de_acceso=sesiones), con_sesion=False) as cliente:
        respuesta = await cliente.post(LOGOUT, headers=cabecera_de_cookie(vigente.sesion_id))

    assert respuesta.status_code == HTTPStatus.NO_CONTENT
    assert respuesta.headers["set-cookie"] == clear_cookie_header(una_config_de_cookie())


async def test_me_devuelve_el_perfil_de_la_sesion_vigente() -> None:
    async with un_cliente(_contenedor_con_usuario(), con_sesion=True) as cliente:
        respuesta = await cliente.get(ME)

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == {
        "nombreCompleto": "Gestor de Prueba",
        "correo": "gestor@minsa.gob.pe",
        "vistas": ["INICIO", "CASOS"],
        "roles": ["GESTOR"],
        "area": None,
    }


async def test_me_sin_sesion_responde_401_unauthorized() -> None:
    async with un_cliente(_contenedor_con_usuario(), con_sesion=False) as cliente:
        respuesta = await cliente.get(ME)

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()["errorCode"] == "UNAUTHORIZED"


async def test_me_con_una_sesion_vencida_responde_invalid_session_y_borra_la_cookie() -> None:
    async with un_cliente(_contenedor_con_usuario(), con_sesion=False) as cliente:
        respuesta = await cliente.get(ME, headers=cabecera_de_cookie("0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"))

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()["errorCode"] == "INVALID_SESSION"
    assert respuesta.headers["set-cookie"] == clear_cookie_header(una_config_de_cookie())
