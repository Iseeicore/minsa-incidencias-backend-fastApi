from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.constants.eventos import (
    EVENTOS_AGRUPADO_SEGUNDOS,
    EVENTOS_CABECERAS,
    EVENTOS_LATIDO_SEGUNDOS,
    EVENTOS_MAX_POR_USUARIO,
    EVENTOS_MAX_TOTAL,
    EVENTOS_REINTENTO_MS,
    EVENTOS_RUTA,
)
from app.constants.limits import MS_PER_SECOND
from app.constants.textos.eventos import (
    EVENTOS_429_DESCRIPCION,
    EVENTOS_DESCRIPCION,
    EVENTOS_EJEMPLO_DE_FLUJO,
    EVENTOS_ETIQUETA,
    EVENTOS_FLUJO_DESCRIPCION,
    EVENTOS_RESUMEN,
)
from app.enums.error_code import ErrorCode
from app.eventos.adapters.http.sse import SuscriptorSse
from app.shared.auth_deps import require_session
from app.shared.http_errors import INTERNAL_RESPONSE, SIN_SESION_RESPONSE, error_response
from app.shared.sesion import SesionActual

if TYPE_CHECKING:
    from app.eventos.application.suscribirse_a_eventos import SuscribirseAEventos

TIPO_DE_FLUJO = EVENTOS_CABECERAS["Content-Type"]
DESCRIPCION = EVENTOS_DESCRIPCION.format(
    reintento=EVENTOS_REINTENTO_MS,
    agrupado=EVENTOS_AGRUPADO_SEGUNDOS * MS_PER_SECOND,
    latido=EVENTOS_LATIDO_SEGUNDOS * MS_PER_SECOND,
    por_usuario=EVENTOS_MAX_POR_USUARIO,
    total=EVENTOS_MAX_TOTAL,
)
FLUJO_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {
        "description": EVENTOS_FLUJO_DESCRIPCION,
        "content": {TIPO_DE_FLUJO: {"schema": {"type": "string"}, "example": EVENTOS_EJEMPLO_DE_FLUJO}},
        "headers": {
            "Cache-Control": {
                "description": "El flujo no se guarda ni se transforma.",
                "schema": {"type": "string", "const": EVENTOS_CABECERAS["Cache-Control"]},
            },
            "X-Accel-Buffering": {
                "description": "Pide al proxy inverso que no acumule el flujo.",
                "schema": {"type": "string", "const": EVENTOS_CABECERAS["X-Accel-Buffering"]},
            },
        },
    }
}
CONEXIONES_RESPONSE = error_response(HTTPStatus.TOO_MANY_REQUESTS, ErrorCode.DEMASIADAS_CONEXIONES)
CONEXIONES_RESPONSE[HTTPStatus.TOO_MANY_REQUESTS]["description"] = EVENTOS_429_DESCRIPCION
SesionDep = Annotated[SesionActual, Depends(require_session)]


def build_eventos_router(suscribirse: SuscribirseAEventos) -> APIRouter:
    router = APIRouter(tags=[EVENTOS_ETIQUETA])

    @router.get(
        EVENTOS_RUTA,
        operation_id="escucharEventos",
        summary=EVENTOS_RESUMEN,
        description=DESCRIPCION,
        response_class=StreamingResponse,
        responses={**FLUJO_RESPONSE, **SIN_SESION_RESPONSE, **CONEXIONES_RESPONSE, **INTERNAL_RESPONSE},
    )
    async def escuchar_eventos(sesion: SesionDep) -> StreamingResponse:
        suscriptor = SuscriptorSse()
        dar_de_baja = suscribirse.execute(sesion, suscriptor)
        return StreamingResponse(
            suscriptor.flujo(dar_de_baja), headers=EVENTOS_CABECERAS, background=BackgroundTask(dar_de_baja)
        )

    return router
