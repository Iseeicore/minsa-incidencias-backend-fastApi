from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, FastAPI

from app.shared.auth_deps import require_session
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
