from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

import structlog
from fastapi import APIRouter, Depends, Request, Response

from app.acceso.adapters.http.login_limits import LoginLimits
from app.acceso.adapters.http.schemas import LoginRequest, PerfilDeSesionResponse
from app.constants.http import SESSION_STATE_KEY
from app.constants.sesion import OPERACION_CIERRE_DE_SESION
from app.constants.textos.usuarios import MENSAJE_REVOCACION_FALLIDA
from app.enums.error_code import ErrorCode
from app.shared.auth_deps import require_session
from app.shared.http_errors import (
    INTERNAL_RESPONSE,
    PAYLOAD_TOO_LARGE_RESPONSE,
    RATE_LIMITED_RESPONSE,
    SIN_SESION_RESPONSE,
    VALIDATION_RESPONSE,
    error_response,
    json_example,
)
from app.shared.sesion import SesionActual
from app.shared.session_cookie import clear_cookie_header, read_session_id, set_cookie_header

if TYPE_CHECKING:
    from app.acceso.application.cerrar_sesion import CerrarSesion
    from app.acceso.application.iniciar_sesion import IniciarSesion
    from app.shared.clock import Clock
    from app.shared.http_security import HttpSecurity
    from app.shared.token_bucket import TokenBucketLimiter

logger = structlog.get_logger()
SET_COOKIE = "set-cookie"
PERFIL_EJEMPLO = {
    "nombreCompleto": "Ana Torres",
    "correo": "ana.torres@minsa.gob.pe",
    "vistas": ["INICIO", "CASOS"],
    "roles": ["GESTOR"],
    "area": {"codigo": "HOSP-01", "nombre": "Hospital Uno", "tipo": "ESTABLECIMIENTO"},
}
PERFIL_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {"description": "Perfil de la sesión vigente.", "content": json_example(PERFIL_EJEMPLO)}
}
FORBIDDEN_RESPONSE = error_response(HTTPStatus.FORBIDDEN, ErrorCode.FORBIDDEN)
INVALID_CREDENTIALS_RESPONSE = error_response(HTTPStatus.UNAUTHORIZED, ErrorCode.INVALID_CREDENTIALS)


def build_acceso_router(
    iniciar_sesion: IniciarSesion,
    cerrar_sesion: CerrarSesion,
    limiter: TokenBucketLimiter,
    security: HttpSecurity,
    clock: Clock,
) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["Autenticación"])
    login_limits = LoginLimits(limiter, security)

    @router.post(
        "/login",
        status_code=HTTPStatus.NO_CONTENT,
        operation_id="iniciarSesion",
        summary="Iniciar sesión.",
        description="Valida el correo y la contraseña y entrega la cookie de sesión firmada; el cuerpo va vacío.",
        dependencies=[Depends(login_limits)],
        responses={
            **VALIDATION_RESPONSE,
            **INVALID_CREDENTIALS_RESPONSE,
            **FORBIDDEN_RESPONSE,
            **PAYLOAD_TOO_LARGE_RESPONSE,
            **RATE_LIMITED_RESPONSE,
            **INTERNAL_RESPONSE,
        },
    )
    async def login(body: LoginRequest, request: Request, response: Response) -> None:
        session_id = await iniciar_sesion.execute(body.correo, body.password)
        anterior = getattr(request.state, SESSION_STATE_KEY, None)
        if isinstance(anterior, SesionActual):
            await cerrar_sesion.de_la_sesion(anterior)
        vence = clock.now() + timedelta(seconds=security.session_max_age_seconds)
        cookie = set_cookie_header(session_id, security.cookies, security.session_max_age_seconds, vence)
        response.headers.append(SET_COOKIE, cookie)

    @router.post(
        "/logout",
        status_code=HTTPStatus.NO_CONTENT,
        operation_id="cerrarSesion",
        summary="Cerrar la sesión.",
        description="Borra la cookie y revoca la sesión; responde 204 aunque la revocación falle.",
        responses={**FORBIDDEN_RESPONSE, **INTERNAL_RESPONSE},
    )
    async def logout(request: Request, response: Response) -> None:
        response.headers.append(SET_COOKIE, clear_cookie_header(security.cookies))
        session_id = read_session_id(request.cookies, security.cookies)
        if session_id is None:
            return
        try:
            await cerrar_sesion.por_id(session_id)
        except Exception:
            logger.exception(MENSAJE_REVOCACION_FALLIDA, operacion=OPERACION_CIERRE_DE_SESION)

    @router.get(
        "/me",
        response_model=PerfilDeSesionResponse,
        operation_id="consultarSesionActual",
        summary="Consultar el perfil de la sesión vigente.",
        description="Devuelve el nombre, el correo, los roles, las vistas habilitadas y el área de la persona.",
        responses={**PERFIL_RESPONSE, **SIN_SESION_RESPONSE, **RATE_LIMITED_RESPONSE, **INTERNAL_RESPONSE},
    )
    async def me(sesion: Annotated[SesionActual, Depends(require_session)]) -> PerfilDeSesionResponse:
        return PerfilDeSesionResponse.desde_sesion(sesion)

    return router
