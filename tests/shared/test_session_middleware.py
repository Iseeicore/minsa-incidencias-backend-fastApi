from http import HTTPStatus
from typing import Annotated
from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.shared.auth_deps import require_session
from app.shared.http_errors import register_error_handlers
from app.shared.sesion import SesionActual
from app.shared.session_cookie import clear_cookie_header
from app.shared.session_middleware import SessionMiddleware
from app.shared.signed_cookie import sign
from tests.helpers.builders import SECRETO_ANTERIOR, SECRETO_DE_PRUEBA, una_config_de_cookie, una_sesion
from tests.helpers.fakes import FixedClock, SesionesEnMemoria

ID_CONOCIDO = una_sesion().sesion_id
ID_DESCONOCIDO = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"


def _cookie(session_id: str, secreto: str = SECRETO_DE_PRUEBA) -> dict[str, str]:
    return {"Cookie": f"gestion_sid={quote(f's:{sign(session_id, secreto)}', safe='')}"}


def _cliente(resolvedor: SesionesEnMemoria) -> AsyncClient:
    app = FastAPI()
    register_error_handlers(app, FixedClock())

    @app.get("/estado")
    async def estado(request: Request) -> dict[str, object]:
        sesion = getattr(request.state, "sesion", None)
        return {
            "usuario": sesion.usuario_id if isinstance(sesion, SesionActual) else None,
            "invalida": getattr(request.state, "sesion_invalida", False),
        }

    @app.get("/protegida")
    async def protegida(sesion: Annotated[SesionActual, Depends(require_session)]) -> dict[str, str]:
        return {"correo": sesion.correo}

    @app.post("/auth/logout")
    async def cerrar() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(SessionMiddleware, resolver=resolvedor, cookies=una_config_de_cookie())
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://prueba")


async def test_sin_cookie_no_hay_sesion_ni_se_consulta_al_resolvedor() -> None:
    resolvedor = SesionesEnMemoria({ID_CONOCIDO: una_sesion()})
    async with _cliente(resolvedor) as cliente:
        respuesta = await cliente.get("/estado")

    assert respuesta.json() == {"usuario": None, "invalida": False}
    assert resolvedor.consultas == []


async def test_una_cookie_valida_con_sesion_conocida_adjunta_la_sesion() -> None:
    resolvedor = SesionesEnMemoria({ID_CONOCIDO: una_sesion()})
    async with _cliente(resolvedor) as cliente:
        respuesta = await cliente.get("/estado", headers=_cookie(ID_CONOCIDO))

    assert respuesta.json() == {"usuario": una_sesion().usuario_id, "invalida": False}
    assert resolvedor.consultas == [ID_CONOCIDO]
    assert "set-cookie" not in respuesta.headers


async def test_la_cookie_firmada_con_el_secreto_anterior_tambien_vale() -> None:
    resolvedor = SesionesEnMemoria({ID_CONOCIDO: una_sesion()})
    async with _cliente(resolvedor) as cliente:
        respuesta = await cliente.get("/estado", headers=_cookie(ID_CONOCIDO, SECRETO_ANTERIOR))

    assert respuesta.json()["usuario"] == una_sesion().usuario_id


async def test_una_sesion_desconocida_se_marca_invalida_y_se_borra_la_cookie() -> None:
    resolvedor = SesionesEnMemoria()
    async with _cliente(resolvedor) as cliente:
        respuesta = await cliente.get("/estado", headers=_cookie(ID_DESCONOCIDO))

    assert respuesta.json() == {"usuario": None, "invalida": True}
    assert respuesta.headers["set-cookie"] == clear_cookie_header(una_config_de_cookie())


async def test_una_ruta_protegida_con_sesion_desconocida_responde_invalid_session() -> None:
    async with _cliente(SesionesEnMemoria()) as cliente:
        respuesta = await cliente.get("/protegida", headers=_cookie(ID_DESCONOCIDO))

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()["errorCode"] == "INVALID_SESSION"
    assert respuesta.json()["message"] == "La sesión no es válida o ya terminó."
    assert respuesta.headers["set-cookie"] == clear_cookie_header(una_config_de_cookie())


async def test_una_ruta_protegida_sin_cookie_responde_unauthorized() -> None:
    async with _cliente(SesionesEnMemoria()) as cliente:
        respuesta = await cliente.get("/protegida")

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()["errorCode"] == "UNAUTHORIZED"


async def test_una_ruta_protegida_con_sesion_valida_responde_200() -> None:
    async with _cliente(SesionesEnMemoria({ID_CONOCIDO: una_sesion()})) as cliente:
        respuesta = await cliente.get("/protegida", headers=_cookie(ID_CONOCIDO))

    assert respuesta.json() == {"correo": una_sesion().correo}


async def test_una_firma_ajena_se_ignora_sin_consultar_ni_borrar_la_cookie() -> None:
    resolvedor = SesionesEnMemoria({ID_CONOCIDO: una_sesion()})
    async with _cliente(resolvedor) as cliente:
        respuesta = await cliente.get("/estado", headers=_cookie(ID_CONOCIDO, "secreto-ajeno-" + "a" * 32))

    assert respuesta.json() == {"usuario": None, "invalida": False}
    assert resolvedor.consultas == []
    assert "set-cookie" not in respuesta.headers


async def test_el_cierre_de_sesion_no_consulta_el_resolvedor() -> None:
    resolvedor = SesionesEnMemoria({ID_CONOCIDO: una_sesion()})
    async with _cliente(resolvedor) as cliente:
        respuesta = await cliente.post("/auth/logout", headers=_cookie(ID_CONOCIDO))

    assert respuesta.status_code == HTTPStatus.OK
    assert resolvedor.consultas == []
