from dataclasses import replace
from http import HTTPStatus
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI

from app.enums.rol_codigo import RolCodigo
from app.enums.vista_codigo import VistaCodigo
from app.shared.auth_deps import require_session, require_vista_y_rol
from app.shared.http_errors import register_error_handlers
from app.shared.sesion import SesionActual
from tests.helpers.app_minima import un_cliente_de
from tests.helpers.builders import una_sesion
from tests.helpers.fakes import FixedClock
from tests.helpers.sesion import SesionDePrueba


def una_app_con_ruta_protegida() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app, FixedClock())

    @app.get("/protegida")
    async def protegida(sesion: Annotated[SesionActual, Depends(require_session)]) -> dict[str, str]:
        return {"correo": sesion.correo}

    return app


async def test_con_sesion_la_ruta_protegida_recibe_la_sesion_actual() -> None:
    app = una_app_con_ruta_protegida()

    async with un_cliente_de(SesionDePrueba(app, una_sesion(correo="ana@minsa.gob.pe"))) as cliente:
        respuesta = await cliente.get("/protegida")

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == {"correo": "ana@minsa.gob.pe"}


async def test_sin_sesion_la_ruta_protegida_responde_401_con_el_mensaje_del_contrato() -> None:
    async with un_cliente_de(una_app_con_ruta_protegida()) as cliente:
        respuesta = await cliente.get("/protegida")

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()["errorCode"] == "UNAUTHORIZED"
    assert respuesta.json()["message"] == "Debes iniciar sesión."


def una_app_con_acceso_a_derivaciones() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app, FixedClock())

    @app.get("/seguimiento")
    async def seguimiento(
        sesion: Annotated[
            SesionActual,
            Depends(require_vista_y_rol(VistaCodigo.DERIVACIONES, RolCodigo.OTRANS, RolCodigo.ADMINISTRADOR)),
        ],
    ) -> dict[str, str]:
        return {"correo": sesion.correo}

    return app


@pytest.mark.parametrize("rol", [RolCodigo.OTRANS, RolCodigo.ADMINISTRADOR])
async def test_con_la_vista_y_uno_de_los_roles_pasa_con_la_sesion(rol: RolCodigo) -> None:
    app = una_app_con_acceso_a_derivaciones()

    async with un_cliente_de(SesionDePrueba(app, una_sesion(roles=(rol,)))) as cliente:
        respuesta = await cliente.get("/seguimiento")

    assert respuesta.status_code == HTTPStatus.OK


@pytest.mark.parametrize("roles", [("GESTOR",), ("ESTABLECIMIENTO",), ()])
async def test_sin_la_vista_o_sin_el_rol_responde_403(roles: tuple[str, ...]) -> None:
    app = una_app_con_acceso_a_derivaciones()

    async with un_cliente_de(SesionDePrueba(app, una_sesion(roles=roles))) as cliente:
        respuesta = await cliente.get("/seguimiento")

    assert respuesta.status_code == HTTPStatus.FORBIDDEN


async def test_con_la_vista_pero_con_otro_rol_responde_403() -> None:
    app = una_app_con_acceso_a_derivaciones()
    sesion = replace(una_sesion(roles=("GESTOR",)), vistas=(VistaCodigo.DERIVACIONES,))

    async with un_cliente_de(SesionDePrueba(app, sesion)) as cliente:
        respuesta = await cliente.get("/seguimiento")

    assert respuesta.status_code == HTTPStatus.FORBIDDEN


async def test_con_el_rol_pero_sin_la_vista_responde_403() -> None:
    app = una_app_con_acceso_a_derivaciones()
    sesion = replace(una_sesion(roles=("OTRANS",)), vistas=())

    async with un_cliente_de(SesionDePrueba(app, sesion)) as cliente:
        respuesta = await cliente.get("/seguimiento")

    assert respuesta.status_code == HTTPStatus.FORBIDDEN


async def test_sin_sesion_el_acceso_a_derivaciones_responde_401() -> None:
    async with un_cliente_de(una_app_con_acceso_a_derivaciones()) as cliente:
        respuesta = await cliente.get("/seguimiento")

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
