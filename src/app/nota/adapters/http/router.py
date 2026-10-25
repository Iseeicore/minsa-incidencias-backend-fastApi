from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Path, Request, Response

from app.enums.error_code import ErrorCode
from app.nota.adapters.http.schemas import CrearNotaRequest, NotaResponse
from app.nota.application.crear_nota import CrearNotaComando
from app.nota.domain.constantes import CODIGO_LENGTH
from app.shared.http_errors import (
    INTERNAL_RESPONSE,
    PAYLOAD_TOO_LARGE_RESPONSE,
    TIMEOUT_RESPONSE,
    UNAVAILABLE_RESPONSE,
    UNPROCESSABLE_RESPONSE,
    error_response,
    json_example,
)

if TYPE_CHECKING:
    from app.nota.application.consultar_nota import ConsultarNota
    from app.nota.application.crear_nota import CrearNota

CODIGO_EJEMPLO = "NOTA-000001"
NOTA_EJEMPLO = {
    "codigo": CODIGO_EJEMPLO,
    "titulo": "Reunión del lunes",
    "contenido": "Revisar los pendientes de la semana",
    "creadaEn": "2026-10-24T12:00:00Z",
}
CREADA_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.CREATED: {
        "description": "Nota creada",
        "headers": {
            "Location": {"description": "Ruta de la nota creada", "schema": {"type": "string"}},
        },
        "content": json_example(NOTA_EJEMPLO),
    }
}
ENCONTRADA_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {"description": "Nota encontrada", "content": json_example(NOTA_EJEMPLO)}
}
NO_ENCONTRADA_RESPONSE = error_response(
    HTTPStatus.NOT_FOUND, ErrorCode.NOTA_NOT_FOUND, "La nota no existe", {"codigo": CODIGO_EJEMPLO}
)
CODIGO_PATH = Path(max_length=CODIGO_LENGTH, examples=[CODIGO_EJEMPLO])


def build_nota_router(crear_nota: CrearNota, consultar_nota: ConsultarNota) -> APIRouter:
    router = APIRouter(prefix="/notas", tags=["notas"])

    @router.post(
        "",
        status_code=HTTPStatus.CREATED,
        response_model=NotaResponse,
        summary="Crear una nota",
        description="Crea una nota con el siguiente código disponible y devuelve su ubicación en la cabecera Location.",
        responses={
            **CREADA_RESPONSE,
            **PAYLOAD_TOO_LARGE_RESPONSE,
            **UNPROCESSABLE_RESPONSE,
            **UNAVAILABLE_RESPONSE,
            **TIMEOUT_RESPONSE,
            **INTERNAL_RESPONSE,
        },
    )
    async def crear(cuerpo: CrearNotaRequest, request: Request, response: Response) -> NotaResponse:
        nota = await crear_nota.execute(CrearNotaComando(titulo=cuerpo.titulo, contenido=cuerpo.contenido))
        response.headers["Location"] = request.url_for("consultar", codigo=nota.codigo.valor).path
        return NotaResponse.desde_dominio(nota)

    @router.get(
        "/{codigo}",
        response_model=NotaResponse,
        summary="Consultar una nota",
        description="Devuelve la nota que tiene el código indicado.",
        responses={
            **ENCONTRADA_RESPONSE,
            **NO_ENCONTRADA_RESPONSE,
            **UNPROCESSABLE_RESPONSE,
            **UNAVAILABLE_RESPONSE,
            **TIMEOUT_RESPONSE,
            **INTERNAL_RESPONSE,
        },
    )
    async def consultar(codigo: Annotated[str, CODIGO_PATH]) -> NotaResponse:
        return NotaResponse.desde_dominio(await consultar_nota.execute(codigo))

    return router
