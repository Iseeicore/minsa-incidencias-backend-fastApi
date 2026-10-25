from dataclasses import dataclass, field
from urllib.parse import parse_qsl

import httpx
from openapi_core import OpenAPI
from openapi_core.datatypes import RequestParameters
from werkzeug.datastructures import Headers, ImmutableMultiDict

from app.composition import Container, create_app, create_v1_app


@dataclass
class _ContractRequest:
    request: httpx.Request
    parameters: RequestParameters = field(init=False)

    def __post_init__(self) -> None:
        self.parameters = RequestParameters(
            query=ImmutableMultiDict(parse_qsl(self.request.url.query.decode())),
            header=Headers(list(self.request.headers.items())),
        )

    @property
    def host_url(self) -> str:
        return f"{self.request.url.scheme}://{self.request.url.netloc.decode()}"

    @property
    def path(self) -> str:
        return self.request.url.path

    @property
    def method(self) -> str:
        return self.request.method.lower()

    @property
    def body(self) -> bytes | None:
        return self.request.content or None

    @property
    def content_type(self) -> str:
        return str(self.request.headers.get("content-type", "")).lower()


@dataclass
class _ContractResponse:
    response: httpx.Response

    @property
    def status_code(self) -> int:
        return self.response.status_code

    @property
    def content_type(self) -> str:
        return str(self.response.headers.get("content-type", "")).lower()

    @property
    def headers(self) -> Headers:
        return Headers(list(self.response.headers.items()))

    @property
    def data(self) -> bytes | None:
        return self.response.content or None


def openapi_raiz(container: Container) -> OpenAPI:
    return OpenAPI.from_dict(create_app(container).openapi())


def openapi_v1(container: Container) -> OpenAPI:
    return OpenAPI.from_dict(create_v1_app(container).openapi())


def validar_contrato(openapi: OpenAPI, respuesta: httpx.Response) -> None:
    openapi.validate_response(_ContractRequest(respuesta.request), _ContractResponse(respuesta))
