from dataclasses import dataclass
from http import HTTPStatus
from http.client import responses as http_reason_phrases
from typing import TYPE_CHECKING

import structlog
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.constants.http import EXAMPLE_PATH, EXAMPLE_TIMESTAMP, JSON_MEDIA_TYPE, TIMESTAMP_FORMAT
from app.constants.textos.errores import (
    GENERIC_HTTP_MESSAGE,
    INTERNAL_ERROR_MESSAGE,
    METHOD_NOT_ALLOWED_MESSAGE,
    PAYLOAD_TOO_LARGE_MESSAGE,
    REQUEST_INVALID_MESSAGE,
    ROUTE_NOT_FOUND_MESSAGE,
    SIN_SESION_MESSAGE,
)
from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.database_timeout import DatabaseTimeout
from app.errors.database_unavailable import DatabaseUnavailable
from app.errors.domain_error import DomainError

if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from app.shared.clock import Clock

type ResponseDoc = dict[int | str, dict[str, object]]

HTTP_STATUS_BY_CATEGORY: dict[ErrorCategory, HTTPStatus] = {
    ErrorCategory.NOT_FOUND: HTTPStatus.NOT_FOUND,
    ErrorCategory.CONFLICT: HTTPStatus.CONFLICT,
    ErrorCategory.BUSINESS_RULE: HTTPStatus.UNPROCESSABLE_ENTITY,
    ErrorCategory.FORBIDDEN: HTTPStatus.FORBIDDEN,
    ErrorCategory.VALIDATION: HTTPStatus.UNPROCESSABLE_ENTITY,
    ErrorCategory.UNAUTHENTICATED: HTTPStatus.UNAUTHORIZED,
    ErrorCategory.UNAVAILABLE: HTTPStatus.SERVICE_UNAVAILABLE,
    ErrorCategory.TIMEOUT: HTTPStatus.GATEWAY_TIMEOUT,
    ErrorCategory.INTERNAL: HTTPStatus.INTERNAL_SERVER_ERROR,
}
ERROR_CODE_BY_HTTP_STATUS: dict[int, tuple[ErrorCode, str]] = {
    HTTPStatus.NOT_FOUND: (ErrorCode.ROUTE_NOT_FOUND, ROUTE_NOT_FOUND_MESSAGE),
    HTTPStatus.METHOD_NOT_ALLOWED: (ErrorCode.METHOD_NOT_ALLOWED, METHOD_NOT_ALLOWED_MESSAGE),
    HTTPStatus.REQUEST_ENTITY_TOO_LARGE: (ErrorCode.PAYLOAD_TOO_LARGE, PAYLOAD_TOO_LARGE_MESSAGE),
}

logger = structlog.get_logger()


class ErrorBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    status_code: int
    error_code: ErrorCode
    message: str
    timestamp: str
    path: str
    details: dict[str, object] | list[object] | None = None


def json_example(value: object) -> dict[str, object]:
    return {JSON_MEDIA_TYPE: {"example": value}}


def error_response(status: HTTPStatus, code: ErrorCode, message: str, details: object = None) -> ResponseDoc:
    example: dict[str, object] = {
        "statusCode": int(status),
        "errorCode": code.value,
        "message": message,
        "timestamp": EXAMPLE_TIMESTAMP,
        "path": EXAMPLE_PATH,
    }
    if details is not None:
        example["details"] = details
    return {status: {"model": ErrorBody, "description": status.phrase, "content": json_example(example)}}


UNPROCESSABLE_RESPONSE = error_response(
    HTTPStatus.UNPROCESSABLE_ENTITY,
    ErrorCode.REQUEST_INVALID,
    REQUEST_INVALID_MESSAGE,
    [{"path": "body.campo", "message": "Field required"}],
)
PAYLOAD_TOO_LARGE_RESPONSE = error_response(
    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    ErrorCode.PAYLOAD_TOO_LARGE,
    ERROR_CODE_BY_HTTP_STATUS[HTTPStatus.REQUEST_ENTITY_TOO_LARGE][1],
)
UNAVAILABLE_RESPONSE = error_response(
    HTTPStatus.SERVICE_UNAVAILABLE, ErrorCode.DATABASE_UNAVAILABLE, DatabaseUnavailable().message
)
TIMEOUT_RESPONSE = error_response(HTTPStatus.GATEWAY_TIMEOUT, ErrorCode.DATABASE_TIMEOUT, DatabaseTimeout().message)
SIN_SESION_RESPONSE = error_response(HTTPStatus.UNAUTHORIZED, ErrorCode.UNAUTHORIZED, SIN_SESION_MESSAGE)
INTERNAL_RESPONSE = error_response(HTTPStatus.INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_ERROR, INTERNAL_ERROR_MESSAGE)


@dataclass(frozen=True, slots=True)
class ErrorPayload:
    status: int
    code: ErrorCode
    message: str
    details: object = None
    headers: dict[str, str] | None = None


def _validation_details(errors: list[dict[str, object]]) -> list[dict[str, str]]:
    return [{"path": ".".join(str(part) for part in error["loc"]), "message": str(error["msg"])} for error in errors]  # type: ignore[attr-defined]


def _response(request: Request, clock: Clock, payload: ErrorPayload) -> JSONResponse:
    body = ErrorBody(
        status_code=payload.status,
        error_code=payload.code,
        message=payload.message,
        timestamp=clock.now().strftime(TIMESTAMP_FORMAT),
        path=request.url.path,
        details=jsonable_encoder(payload.details),
    )
    return JSONResponse(
        status_code=payload.status,
        content=body.model_dump(by_alias=True, exclude_none=True),
        headers=payload.headers,
    )


def register_error_handlers(app: FastAPI, clock: Clock) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
        status = HTTP_STATUS_BY_CATEGORY[error.category]
        message = error.message
        if status == HTTPStatus.INTERNAL_SERVER_ERROR:
            logger.error(
                "internal_domain_error", path=request.url.path, error_type=type(error).__name__, exc_info=error
            )
            message = INTERNAL_ERROR_MESSAGE
        return _response(request, clock, ErrorPayload(status, error.error_code, message, error.details))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(request: Request, error: RequestValidationError) -> JSONResponse:
        payload = ErrorPayload(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            ErrorCode.REQUEST_INVALID,
            REQUEST_INVALID_MESSAGE,
            _validation_details(error.errors()),  # type: ignore[arg-type]
        )
        return _response(request, clock, payload)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, error: StarletteHTTPException) -> JSONResponse:
        if error.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            logger.error("http_exception_server_error", path=request.url.path, status=error.status_code)
            server_payload = ErrorPayload(
                error.status_code,
                ErrorCode.INTERNAL_ERROR,
                INTERNAL_ERROR_MESSAGE,
                headers=dict(error.headers) if error.headers else None,
            )
            return _response(request, clock, server_payload)
        code, message = ERROR_CODE_BY_HTTP_STATUS.get(
            error.status_code,
            (ErrorCode.HTTP_ERROR, http_reason_phrases.get(error.status_code, GENERIC_HTTP_MESSAGE)),
        )
        headers = dict(error.headers) if error.headers else None
        return _response(request, clock, ErrorPayload(error.status_code, code, message, headers=headers))


class UnexpectedErrorMiddleware:
    def __init__(self, app: ASGIApp, clock: Clock) -> None:
        self._app = app
        self._clock = clock

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        response_started = False

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self._app(scope, receive, tracking_send)
        except Exception:
            if response_started:
                raise
            request = Request(scope)
            logger.exception("unexpected_error", path=request.url.path)
            payload = ErrorPayload(HTTPStatus.INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_ERROR, INTERNAL_ERROR_MESSAGE)
            await _response(request, self._clock, payload)(scope, receive, send)
