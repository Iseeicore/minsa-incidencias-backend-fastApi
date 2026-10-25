from http import HTTPStatus
from typing import Any

import pytest

from app.enums.evento_nombre import EventoNombre
from app.enums.motivo_de_cierre import MotivoDeCierre
from app.errors.demasiadas_conexiones import DemasiadasConexiones
from app.errors.sesion_invalida import SesionInvalida
from app.eventos.application.suscribirse_a_eventos import SuscribirseAEventos
from app.eventos.domain.ports import DarDeBaja, Suscriptor
from app.shared.sesion import SesionActual
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.contract import openapi_del_nodo, validar_contrato

RUTA = "/v1/eventos"


class SuscribirseFalso:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.sesiones: list[SesionActual] = []
        self.bajas = 0

    def execute(self, sesion: SesionActual, suscriptor: Suscriptor) -> DarDeBaja:
        if self.error is not None:
            raise self.error
        self.sesiones.append(sesion)
        suscriptor.enviar(EventoNombre.CAMBIO)
        suscriptor.latido()
        suscriptor.enviar(EventoNombre.SESION)
        suscriptor.cerrar(MotivoDeCierre.SESION_INVALIDA)
        return self._dar_de_baja

    def _dar_de_baja(self) -> None:
        self.bajas += 1


def _contenedor(falso: SuscribirseFalso) -> Any:  # noqa: ANN401
    return un_contenedor(suscribirse=falso)  # type: ignore[arg-type]


async def test_abre_el_flujo_con_las_cabeceras_de_sse_y_entrega_los_eventos() -> None:
    falso = SuscribirseFalso()
    async with un_cliente(_contenedor(falso)) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.headers["content-type"] == "text/event-stream"
    assert respuesta.headers["cache-control"] == "no-cache, no-transform"
    assert respuesta.headers["x-accel-buffering"] == "no"
    assert respuesta.text == "retry: 5000\n\nevent: cambio\ndata: {}\n\n: latido\n\nevent: sesion\ndata: {}\n\n"
    assert len(falso.sesiones) == 1
    assert falso.bajas >= 1


async def test_sin_sesion_responde_401_y_no_suscribe_a_nadie() -> None:
    falso = SuscribirseFalso()
    async with un_cliente(_contenedor(falso), con_sesion=False) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()["errorCode"] == "UNAUTHORIZED"
    assert falso.sesiones == []
    validar_contrato(openapi_del_nodo(), respuesta)


@pytest.mark.parametrize(
    ("error", "estado", "codigo"),
    [
        (SesionInvalida(), HTTPStatus.UNAUTHORIZED, "INVALID_SESSION"),
        (DemasiadasConexiones(), HTTPStatus.TOO_MANY_REQUESTS, "DEMASIADAS_CONEXIONES"),
    ],
)
async def test_si_no_se_puede_suscribir_responde_con_el_error_en_json_y_sin_abrir_el_flujo(
    error: Exception, estado: HTTPStatus, codigo: str
) -> None:
    async with un_cliente(_contenedor(SuscribirseFalso(error=error))) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == estado
    assert respuesta.headers["content-type"].startswith("application/json")
    assert respuesta.json()["errorCode"] == codigo
    assert "x-accel-buffering" not in respuesta.headers
    assert "retry:" not in respuesta.text
    assert "retry-after" not in respuesta.headers
    validar_contrato(openapi_del_nodo(), respuesta)


def test_el_caso_de_uso_real_es_el_que_se_usa_por_defecto() -> None:
    assert isinstance(un_contenedor().suscribirse_a_eventos, SuscribirseAEventos)
