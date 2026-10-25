import json
from http import HTTPStatus

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Message, Receive, Scope, Send

from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError
from app.shared.http_errors import UnexpectedErrorMiddleware, register_error_handlers
from app.shared.logging import configure_logging
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.app_minima import un_cliente_de, una_app_minima
from tests.helpers.fakes import FixedClock, RaisingPlazoRepository

RUTA = "/v1/catalogos/plazos"


class SondaQueFalla:
    async def ping(self) -> bool:
        message = "secreto interno de la base"
        raise RuntimeError(message)


class ErrorInternoDePrueba(DomainError):
    category = ErrorCategory.INTERNAL
    error_code = ErrorCode.INTERNAL_ERROR

    def __init__(self) -> None:
        super().__init__("detalle interno del dominio")


@pytest.mark.parametrize("ruta", ["/no-existe", "/v1/no-existe"], ids=["raiz", "v1"])
async def test_una_ruta_inexistente_responde_con_el_formato_unico(ruta: str) -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get(ruta)

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json() == {
        "success": False,
        "statusCode": 404,
        "errorCode": "NOT_FOUND",
        "message": "El recurso solicitado no existe.",
        "timestamp": "2026-10-24T12:00:00.000Z",
        "path": ruta,
    }


async def test_un_metodo_no_permitido_responde_404_como_el_node() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.delete(RUTA)

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["errorCode"] == "NOT_FOUND"
    assert respuesta.json()["path"] == RUTA


async def test_un_error_inesperado_responde_500_sin_filtrar_el_mensaje_interno() -> None:
    async with un_cliente(un_contenedor(sonda=SondaQueFalla())) as cliente:
        respuesta = await cliente.get("/salud/listo")

    assert respuesta.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert respuesta.json()["errorCode"] == "INTERNAL_ERROR"
    assert respuesta.json()["message"] == "Ocurrió un error interno. Inténtalo más tarde."
    assert "secreto" not in respuesta.text


def _eventos(salida: str) -> list[dict[str, object]]:
    return [json.loads(linea) for linea in salida.splitlines() if linea.startswith("{")]


async def test_un_error_inesperado_en_v1_responde_500_unificado_y_se_registra_una_sola_vez(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("info")
    contenedor = un_contenedor(RaisingPlazoRepository(RuntimeError("detalle interno de la base")))

    async with un_cliente(contenedor) as cliente:
        respuesta = await cliente.get(RUTA)

    registros = [evento for evento in _eventos(capsys.readouterr().out) if evento["event"] == "unexpected_error"]
    assert respuesta.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert respuesta.json()["errorCode"] == "INTERNAL_ERROR"
    assert "detalle interno" not in respuesta.text
    assert len(registros) == 1
    assert registros[0]["path"] == RUTA


async def test_un_error_de_dominio_interno_responde_500_y_se_registra(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("info")
    contenedor = un_contenedor(RaisingPlazoRepository(ErrorInternoDePrueba()))

    async with un_cliente(contenedor) as cliente:
        respuesta = await cliente.get(RUTA)

    registros = [evento for evento in _eventos(capsys.readouterr().out) if evento["event"] == "internal_domain_error"]
    assert respuesta.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert respuesta.json()["message"] == "Ocurrió un error interno. Inténtalo más tarde."
    assert "detalle interno" not in respuesta.text
    assert len(registros) == 1


async def test_el_detalle_de_un_cuerpo_invalido_trae_solo_ruta_y_mensaje_sin_repetir_lo_enviado() -> None:
    async with un_cliente_de(una_app_minima()) as cliente:
        respuesta = await cliente.post("/eco", json={"texto": 12345, "otro": "dato-del-cliente"})

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["success"] is False
    assert respuesta.json()["errorCode"] == "VALIDATION_FAILED"
    assert respuesta.json()["message"] == "Los datos enviados no son válidos."
    detalles = respuesta.json()["details"]
    assert {"path": "texto", "message": "Input should be a valid string"} in detalles
    assert all(set(detalle) == {"path", "message"} for detalle in detalles)
    assert "dato-del-cliente" not in respuesta.text
    assert "12345" not in respuesta.text


async def test_un_json_mal_formado_responde_400_sin_detalles() -> None:
    async with un_cliente_de(una_app_minima()) as cliente:
        respuesta = await cliente.post("/eco", content="{no es json", headers={"Content-Type": "application/json"})

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["errorCode"] == "VALIDATION_FAILED"
    assert "details" not in respuesta.json()


@pytest.mark.parametrize(
    ("estado", "codigo"),
    [(401, "UNAUTHORIZED"), (403, "FORBIDDEN"), (413, "PAYLOAD_TOO_LARGE"), (429, "RATE_LIMITED")],
)
async def test_los_estados_http_del_contrato_conservan_su_codigo(estado: int, codigo: str) -> None:
    app = FastAPI()
    register_error_handlers(app, FixedClock())

    @app.get("/estado")
    async def estado_http() -> None:
        raise StarletteHTTPException(status_code=estado)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://prueba") as cliente:
        respuesta = await cliente.get("/estado")

    assert (respuesta.status_code, respuesta.json()["errorCode"]) == (estado, codigo)


async def test_un_estado_http_no_estandar_no_rompe_el_manejador() -> None:
    app = FastAPI()
    register_error_handlers(app, FixedClock())

    @app.get("/raro")
    async def raro() -> None:
        raise StarletteHTTPException(status_code=499)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://prueba") as cliente:
        respuesta = await cliente.get("/raro")

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["errorCode"] == "VALIDATION_FAILED"


async def _descartar(message: Message) -> None:  # noqa: ARG001
    return None


async def _sin_receive() -> Message:
    return {"type": "http.request"}


async def test_el_middleware_deja_pasar_los_alcances_que_no_son_http() -> None:
    recibidos: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:  # noqa: ARG001
        recibidos.append(scope["type"])

    await UnexpectedErrorMiddleware(app, FixedClock())({"type": "lifespan"}, _sin_receive, _descartar)

    assert recibidos == ["lifespan"]


async def test_el_middleware_no_responde_dos_veces_si_el_error_llega_con_la_respuesta_empezada() -> None:
    enviados: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:  # noqa: ARG001
        await send({"type": "http.response.start", "status": 200, "headers": []})
        message = "falla a mitad de la respuesta"
        raise RuntimeError(message)

    async def send(message: Message) -> None:
        enviados.append(message["type"])

    with pytest.raises(RuntimeError, match="mitad"):
        await UnexpectedErrorMiddleware(app, FixedClock())(
            {"type": "http", "method": "GET", "path": "/x", "headers": [], "query_string": b""}, _sin_receive, send
        )

    assert enviados == ["http.response.start"]


@pytest.mark.parametrize("estado", [500, 502, 503], ids=["500", "502", "503"])
async def test_un_error_http_del_servidor_lanzado_a_mano_se_registra_y_no_filtra_su_detalle(
    capsys: pytest.CaptureFixture[str], estado: int
) -> None:
    configure_logging("info")
    app = FastAPI()
    register_error_handlers(app, FixedClock())

    @app.get("/manual")
    async def manual() -> None:
        raise StarletteHTTPException(status_code=estado, detail="detalle interno del servidor")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://prueba") as cliente:
        respuesta = await cliente.get("/manual")

    registros = [e for e in _eventos(capsys.readouterr().out) if e["event"] == "http_exception_server_error"]
    assert respuesta.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert respuesta.json()["errorCode"] == "INTERNAL_ERROR"
    assert respuesta.json()["message"] == "Ocurrió un error interno. Inténtalo más tarde."
    assert "detalle interno" not in respuesta.text
    assert len(registros) == 1
