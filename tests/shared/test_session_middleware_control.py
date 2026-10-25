from dataclasses import replace
from typing import Annotated
from urllib.parse import quote

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.shared.auth_deps import require_session
from app.shared.http_errors import register_error_handlers
from app.shared.sesion import SesionActual
from app.shared.session_middleware import SessionMiddleware
from app.shared.signed_cookie import sign
from tests.helpers.builders import SECRETO_DE_PRUEBA, una_config_de_cookie, una_sesion
from tests.helpers.eventos_en_memoria import ControlDePrueba
from tests.helpers.fakes import FixedClock, SesionesEnMemoria

ID = una_sesion().sesion_id


class _ErrorDeRuta(Exception):
    pass


def _cookie() -> dict[str, str]:
    return {"Cookie": f"gestion_sid={quote(f's:{sign(ID, SECRETO_DE_PRUEBA)}', safe='')}"}


def _cliente(control: ControlDePrueba) -> AsyncClient:
    app = FastAPI()
    register_error_handlers(app, FixedClock())

    @app.get("/vigente")
    async def vigente(sesion: Annotated[SesionActual, Depends(require_session)]) -> dict[str, bool]:
        assert sesion.control_eventos is not None
        return {"vigente": sesion.control_eventos.vigente()}

    @app.get("/falla")
    async def falla() -> None:
        raise _ErrorDeRuta

    resolvedor = SesionesEnMemoria({ID: replace(una_sesion(), control_eventos=control)})
    app.add_middleware(SessionMiddleware, resolver=resolvedor, cookies=una_config_de_cookie())
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://prueba")


async def test_la_ruta_ve_el_control_vigente_y_al_terminar_la_respuesta_se_libera() -> None:
    control = ControlDePrueba()
    async with _cliente(control) as cliente:
        respuesta = await cliente.get("/vigente", headers=_cookie())

    assert respuesta.json() == {"vigente": True}
    assert control.activo is False


async def test_aunque_la_ruta_falle_el_control_se_libera() -> None:
    control = ControlDePrueba()
    async with _cliente(control) as cliente:
        with pytest.raises(_ErrorDeRuta):
            await cliente.get("/falla", headers=_cookie())

    assert control.activo is False
