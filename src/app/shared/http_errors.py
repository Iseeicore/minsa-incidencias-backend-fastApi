from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Literal

import structlog
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.constants.http import (
    EXAMPLE_PATH,
    EXAMPLE_TIMESTAMP,
    JSON_INVALID_ERROR_TYPE,
    JSON_MEDIA_TYPE,
    TIMESTAMP_PRECISION,
    UTC_OFFSET_SUFFIX,
    UTC_ZULU_SUFFIX,
    VALIDATION_LOCATIONS,
)
from app.constants.textos.errores import DEFAULT_ERROR_MESSAGES
from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
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
    ErrorCategory.VALIDATION: HTTPStatus.BAD_REQUEST,
    ErrorCategory.UNAUTHENTICATED: HTTPStatus.UNAUTHORIZED,
    ErrorCategory.PAYLOAD_TOO_LARGE: HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    ErrorCategory.RATE_LIMITED: HTTPStatus.TOO_MANY_REQUESTS,
    ErrorCategory.NOT_IMPLEMENTED: HTTPStatus.NOT_IMPLEMENTED,
    ErrorCategory.UNAVAILABLE: HTTPStatus.SERVICE_UNAVAILABLE,
    ErrorCategory.INTERNAL: HTTPStatus.INTERNAL_SERVER_ERROR,
}
HTTP_ERROR_BY_STATUS: dict[int, tuple[HTTPStatus, ErrorCode]] = {
    HTTPStatus.UNAUTHORIZED: (HTTPStatus.UNAUTHORIZED, ErrorCode.UNAUTHORIZED),
    HTTPStatus.FORBIDDEN: (HTTPStatus.FORBIDDEN, ErrorCode.FORBIDDEN),
    HTTPStatus.NOT_FOUND: (HTTPStatus.NOT_FOUND, ErrorCode.NOT_FOUND),
    HTTPStatus.METHOD_NOT_ALLOWED: (HTTPStatus.NOT_FOUND, ErrorCode.NOT_FOUND),
    HTTPStatus.REQUEST_ENTITY_TOO_LARGE: (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, ErrorCode.PAYLOAD_TOO_LARGE),
    HTTPStatus.TOO_MANY_REQUESTS: (HTTPStatus.TOO_MANY_REQUESTS, ErrorCode.RATE_LIMITED),
}
CLIENT_ERROR_FALLBACK = (HTTPStatus.BAD_REQUEST, ErrorCode.VALIDATION_FAILED)
SERVER_ERROR_FALLBACK = (HTTPStatus.INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_ERROR)

logger = structlog.get_logger()


class ErrorDetail(BaseModel):
    path: str
    message: str


class ErrorBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    success: Literal[False] = False
    status_code: int
    error_code: ErrorCode
    message: str
    timestamp: str
    path: str
    details: list[ErrorDetail] | None = None


def json_example(value: object) -> dict[str, object]:
    return {JSON_MEDIA_TYPE: {"example": value}}


def error_response(status: HTTPStatus, code: ErrorCode, details: object = None) -> ResponseDoc:
    example: dict[str, object] = {
        "success": False,
        "statusCode": int(status),
        "errorCode": code.value,
        "message": DEFAULT_ERROR_MESSAGES[code],
        "timestamp": EXAMPLE_TIMESTAMP,
        "path": EXAMPLE_PATH,
    }
    if details is not None:
        example["details"] = details
    return {status: {"model": ErrorBody, "description": status.phrase, "content": json_example(example)}}


VALIDATION_RESPONSE = error_response(
    HTTPStatus.BAD_REQUEST, ErrorCode.VALIDATION_FAILED, [{"path": "campo", "message": "Field required"}]
)
PAYLOAD_TOO_LARGE_RESPONSE = error_response(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, ErrorCode.PAYLOAD_TOO_LARGE)
SIN_SESION_RESPONSE = error_response(HTTPStatus.UNAUTHORIZED, ErrorCode.UNAUTHORIZED)
RATE_LIMITED_RESPONSE = error_response(HTTPStatus.TOO_MANY_REQUESTS, ErrorCode.RATE_LIMITED)
INTERNAL_RESPONSE = error_response(HTTPStatus.INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_ERROR)


@dataclass(frozen=True, slots=True)
class ErrorPayload:
    status: int
    code: ErrorCode
    message: str
    details: object = None
    headers: dict[str, str] | None = None


def _validation_details(errors: list[dict[str, object]]) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for error in errors:
        location = [str(part) for part in error["loc"]]  # type: ignore[attr-defined]
        if location and location[0] in VALIDATION_LOCATIONS:
            location = location[1:]
        details.append({"path": ".".join(location), "message": str(error["msg"])})
    return details


def _has_malformed_json(errors: list[dict[str, object]]) -> bool:
    return any(error["type"] == JSON_INVALID_ERROR_TYPE for error in errors)


def _timestamp(clock: Clock) -> str:
    return clock.now().isoformat(timespec=TIMESTAMP_PRECISION).replace(UTC_OFFSET_SUFFIX, UTC_ZULU_SUFFIX)


def _response(request: Request, clock: Clock, payload: ErrorPayload) -> JSONResponse:
    body = ErrorBody(
        status_code=payload.status,
        error_code=payload.code,
        message=payload.message,
        timestamp=_timestamp(clock),
        path=request.url.path,
        details=jsonable_encoder(payload.details),
    )
    return JSONResponse(
        status_code=payload.status,
        content=body.model_dump(by_alias=True, exclude_none=True),
        headers=payload.headers,
    )


def domain_error_response(
    request: Request, clock: Clock, error: DomainError, headers: dict[str, str] | None = None
) -> JSONResponse:
    status = HTTP_STATUS_BY_CATEGORY[error.category]
    return _response(request, clock, ErrorPayload(status, error.error_code, error.message, error.details, headers))


def register_error_handlers(app: FastAPI, clock: Clock) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
        status = HTTP_STATUS_BY_CATEGORY[error.category]
        message = error.message
        if status == HTTPStatus.INTERNAL_SERVER_ERROR:
            logger.error(
                "internal_domain_error", path=request.url.path, error_type=type(error).__name__, exc_info=error
            )
            message = DEFAULT_ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR]
        return _response(request, clock, ErrorPayload(status, error.error_code, message, error.details))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(request: Request, error: RequestValidationError) -> JSONResponse:
        errors: list[dict[str, object]] = error.errors()  # type: ignore[assignment]
        details = None if _has_malformed_json(errors) else _validation_details(errors)
        payload = ErrorPayload(
            HTTPStatus.BAD_REQUEST,
            ErrorCode.VALIDATION_FAILED,
            DEFAULT_ERROR_MESSAGES[ErrorCode.VALIDATION_FAILED],
            details,
        )
        return _response(request, clock, payload)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, error: StarletteHTTPException) -> JSONResponse:
        headers = dict(error.headers) if error.headers else None
        if error.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            logger.error("http_exception_server_error", path=request.url.path, status=error.status_code)
            status, code = SERVER_ERROR_FALLBACK
        else:
            status, code = HTTP_ERROR_BY_STATUS.get(error.status_code, CLIENT_ERROR_FALLBACK)
        return _response(request, clock, ErrorPayload(status, code, DEFAULT_ERROR_MESSAGES[code], headers=headers))


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
            code = ErrorCode.INTERNAL_ERROR
            payload = ErrorPayload(HTTPStatus.INTERNAL_SERVER_ERROR, code, DEFAULT_ERROR_MESSAGES[code])
            await _response(request, self._clock, payload)(scope, receive, send)
