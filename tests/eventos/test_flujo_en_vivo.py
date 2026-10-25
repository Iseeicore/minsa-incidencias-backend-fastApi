import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
import pytest
import uvicorn
from sqlalchemy.ext.asyncio import AsyncEngine

from app.composition import create_app
from app.config.settings import Settings
from app.constants.eventos import EVENTOS_MAX_POR_USUARIO
from app.shared.token_bucket import TokenBucketLimiter
from app.wiring import Eventos, build_container, build_eventos
from tests.helpers.base import CLAVE_DE_PRUEBA, sembrar_usuario
from tests.helpers.casos import EstablecimientoSembrado, sembrar_caso, sembrar_establecimiento
from tests.helpers.registro_en_memoria import RegistroEnMemoria

if TYPE_CHECKING:
    from fastapi import FastAPI

pytestmark = pytest.mark.integration

ORIGEN = "https://app.minsa.gob.pe"
ESPERA = 8
SILENCIO = 2.5
REINTENTO = "retry: 5000\n\n"
AVISO = "event: cambio\ndata: {}\n\n"
FIN_DE_SESION = "event: sesion\ndata: {}\n\n"


@dataclass(frozen=True, slots=True)
class Servidor:
    puerto: int
    eventos: Eventos


def _settings(engine: AsyncEngine) -> Settings:
    url = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    return Settings(
        _env_file=None, database_url=url, cookie_secret="s" * 32, node_env="development", cors_origins=[ORIGEN]
    )


@asynccontextmanager
async def _servidor_real(engine: AsyncEngine) -> AsyncIterator[Servidor]:
    settings = _settings(engine)
    eventos = build_eventos(settings, engine, RegistroEnMemoria())
    contenedor = build_container(settings, engine, TokenBucketLimiter(), eventos.centro)

    @asynccontextmanager
    async def vida(_: FastAPI) -> AsyncIterator[None]:
        await eventos.escuchar.iniciar()
        yield
        eventos.centro.cerrar_todo()
        await eventos.escuchar.detener()

    config = uvicorn.Config(
        create_app(contenedor, vida), host="127.0.0.1", port=0, log_level="warning", timeout_graceful_shutdown=5
    )
    servidor = uvicorn.Server(config)
    tarea = asyncio.create_task(servidor.serve())
    async with asyncio.timeout(ESPERA):
        while not servidor.started:  # noqa: ASYNC110
            await asyncio.sleep(0.02)
    try:
        yield Servidor(servidor.servers[0].sockets[0].getsockname()[1], eventos)
    finally:
        servidor.should_exit = True
        async with asyncio.timeout(ESPERA):
            await tarea


@asynccontextmanager
async def _cliente_con_sesion(puerto: int, correo: str) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        base_url=f"http://127.0.0.1:{puerto}", headers={"Origin": ORIGEN}, timeout=ESPERA
    ) as c:
        login = await c.post("/v1/auth/login", json={"correo": correo, "password": CLAVE_DE_PRUEBA})
        assert login.status_code == httpx.codes.NO_CONTENT
        yield c


async def _leer_hasta(trozos: AsyncIterator[str], esperado: str) -> str:
    acumulado = ""
    async with asyncio.timeout(ESPERA):
        async for trozo in trozos:
            acumulado += trozo
            if acumulado.endswith(esperado):
                break
    return acumulado


async def _escenario(engine: AsyncEngine) -> EstablecimientoSembrado:
    uno = await sembrar_establecimiento(engine, 10, "Hospital Uno")
    dos = await sembrar_establecimiento(engine, 11, "Hospital Dos")
    await sembrar_usuario(engine, "uno@minsa.gob.pe", "GESTOR", uno.area_id, nombre="Gestor Uno")
    await sembrar_usuario(engine, "dos@minsa.gob.pe", "GESTOR", dos.area_id, nombre="Gestor Dos")
    await sembrar_usuario(engine, "admin@minsa.gob.pe", "ADMINISTRADOR", None, nombre="Admin")
    return uno


async def test_el_flujo_real_avisa_solo_a_quien_ve_el_cambio(engine: AsyncEngine) -> None:
    hospital_uno = await _escenario(engine)
    async with (
        _servidor_real(engine) as servidor,
        _cliente_con_sesion(servidor.puerto, "uno@minsa.gob.pe") as uno,
        _cliente_con_sesion(servidor.puerto, "dos@minsa.gob.pe") as dos,
        uno.stream("GET", "/v1/eventos") as flujo_uno,
        dos.stream("GET", "/v1/eventos") as flujo_dos,
    ):
        assert flujo_uno.status_code == httpx.codes.OK
        assert flujo_uno.headers["content-type"] == "text/event-stream"
        assert flujo_uno.headers["cache-control"] == "no-cache, no-transform"
        assert flujo_uno.headers["x-accel-buffering"] == "no"
        trozos_uno, trozos_dos = flujo_uno.aiter_text(), flujo_dos.aiter_text()
        assert await _leer_hasta(trozos_uno, REINTENTO) == REINTENTO
        assert await _leer_hasta(trozos_dos, REINTENTO) == REINTENTO
        assert servidor.eventos.centro.conectados == 2

        await sembrar_caso(engine, categoria="QUEJA", establecimiento=hospital_uno)

        assert await _leer_hasta(trozos_uno, AVISO) == AVISO
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(anext(trozos_dos), SILENCIO)


async def test_revocar_la_sesion_envia_sesion_y_cierra_el_flujo(engine: AsyncEngine) -> None:
    await _escenario(engine)
    async with (
        _servidor_real(engine) as servidor,
        _cliente_con_sesion(servidor.puerto, "uno@minsa.gob.pe") as uno,
        uno.stream("GET", "/v1/eventos") as flujo,
    ):
        trozos = flujo.aiter_text()
        assert await _leer_hasta(trozos, REINTENTO) == REINTENTO

        cierre = await uno.post("/v1/auth/logout")

        assert cierre.status_code == httpx.codes.NO_CONTENT
        assert await _leer_hasta(trozos, FIN_DE_SESION) == FIN_DE_SESION
        assert [trozo async for trozo in trozos] == []
        async with asyncio.timeout(ESPERA):
            while servidor.eventos.centro.conectados:  # noqa: ASYNC110
                await asyncio.sleep(0.02)


async def test_el_cuarto_flujo_de_un_usuario_recibe_429_sin_tocar_los_abiertos(engine: AsyncEngine) -> None:
    await _escenario(engine)
    async with (
        _servidor_real(engine) as servidor,
        _cliente_con_sesion(servidor.puerto, "uno@minsa.gob.pe") as uno,
        AsyncExitStack() as pila,
    ):
        abiertos = []
        for _ in range(EVENTOS_MAX_POR_USUARIO):
            flujo = await pila.enter_async_context(uno.stream("GET", "/v1/eventos"))
            abiertos.append(flujo.aiter_text())
            assert await _leer_hasta(abiertos[-1], REINTENTO) == REINTENTO

        rechazado = await uno.get("/v1/eventos")

        assert rechazado.status_code == httpx.codes.TOO_MANY_REQUESTS
        assert rechazado.json()["errorCode"] == "DEMASIADAS_CONEXIONES"
        assert rechazado.headers["content-type"].startswith("application/json")
        assert "retry-after" not in rechazado.headers
        assert servidor.eventos.centro.conectados == EVENTOS_MAX_POR_USUARIO


async def test_sin_sesion_el_flujo_responde_401(engine: AsyncEngine) -> None:
    async with (
        _servidor_real(engine) as servidor,
        httpx.AsyncClient(base_url=f"http://127.0.0.1:{servidor.puerto}") as anonimo,
    ):
        respuesta = await anonimo.get("/v1/eventos")

        assert respuesta.status_code == httpx.codes.UNAUTHORIZED
        assert respuesta.json()["errorCode"] == "UNAUTHORIZED"
        assert servidor.eventos.centro.conectados == 0


async def test_al_apagar_se_cierran_los_flujos_y_el_servidor_termina_sin_esperar_al_cliente(
    engine: AsyncEngine,
) -> None:
    await _escenario(engine)
    async with (
        _servidor_real(engine) as servidor,
        _cliente_con_sesion(servidor.puerto, "admin@minsa.gob.pe") as admin,
        admin.stream("GET", "/v1/eventos") as flujo,
    ):
        trozos = flujo.aiter_text()
        assert await _leer_hasta(trozos, REINTENTO) == REINTENTO

        servidor.eventos.centro.cerrar_todo()

        assert [trozo async for trozo in trozos] == []
        assert servidor.eventos.centro.conectados == 0
