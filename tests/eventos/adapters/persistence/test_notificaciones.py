import asyncio
from typing import TYPE_CHECKING

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.constants.eventos import CANAL_CAMBIOS_INCIDENCIAS, EVENTOS_TIPO_DE_DISPARADOR, VERSION_DE_NOTIFICACION
from app.eventos.adapters.persistence.notificaciones import AbridorDeConexionPostgres, SqlInstaladorDeNotificaciones
from app.eventos.application.ports import NotificacionDeCanal
from app.eventos.domain.cambio_de_incidencia import CambioDeIncidencia
from app.eventos.domain.leer_cambio import leer_cambio
from app.shared.transaction import transaction
from tests.helpers.base import consultar
from tests.helpers.casos import sembrar_caso

if TYPE_CHECKING:
    from app.eventos.application.ports import ConexionDeNotificaciones

pytestmark = pytest.mark.integration

ESPERA_MAXIMA = 3
ESPERA_PARA_SILENCIO = 0.5


def _url(engine: AsyncEngine) -> str:
    return engine.url.set(drivername="postgresql").render_as_string(hide_password=False)


async def _abrir(engine: AsyncEngine) -> ConexionDeNotificaciones:
    await SqlInstaladorDeNotificaciones(engine).instalar()
    return await AbridorDeConexionPostgres(_url(engine), 5).abrir()


async def _siguiente(conexion: ConexionDeNotificaciones, espera: float = ESPERA_MAXIMA) -> NotificacionDeCanal:
    return await asyncio.wait_for(anext(conexion.notificaciones()), timeout=espera)


async def _recoger(conexion: ConexionDeNotificaciones, cantidad: int) -> list[NotificacionDeCanal]:
    avisos: list[NotificacionDeCanal] = []
    async with asyncio.timeout(ESPERA_MAXIMA):
        async for aviso in conexion.notificaciones():
            avisos.append(aviso)
            if len(avisos) == cantidad:
                break
    return avisos


async def test_instalar_dos_veces_deja_un_solo_disparador_con_la_version_vigente(engine: AsyncEngine) -> None:
    instalador = SqlInstaladorDeNotificaciones(engine)

    await instalador.instalar()
    await instalador.instalar()

    filas = await consultar(
        engine,
        "SELECT CAST(t.tgtype AS int), position(:version IN pg_get_functiondef(t.tgfoid)) > 0"
        " FROM pg_trigger t WHERE t.tgname = 'trg_incidencia_paciente_notificar_cambio'"
        " AND t.tgrelid = 'chatbot.incidencia_paciente'::regclass AND NOT t.tgisinternal",
        version=VERSION_DE_NOTIFICACION,
    )
    assert filas == [(EVENTOS_TIPO_DE_DISPARADOR, True)]


async def test_una_incidencia_nueva_avisa_tras_el_commit_con_alcance_vacio(engine: AsyncEngine) -> None:
    conexion = await _abrir(engine)
    try:
        await sembrar_caso(engine, categoria=None)

        aviso = await _siguiente(conexion)

        assert aviso.canal == CANAL_CAMBIOS_INCIDENCIAS
        assert leer_cambio(aviso.payload) == CambioDeIncidencia(None, None, None, None)
    finally:
        await conexion.cerrar()


async def test_clasificar_un_caso_avisa_con_la_categoria_y_el_area_nuevas(engine: AsyncEngine) -> None:
    conexion = await _abrir(engine)
    try:
        await sembrar_caso(engine, categoria="DENUNCIA_CORRUPCION")

        avisos = await _recoger(conexion, 2)

        [(categoria,)] = await consultar(
            engine, "SELECT id FROM catalogo.categoria_incidencia WHERE codigo = 'DENUNCIA_CORRUPCION'"
        )
        [(area,)] = await consultar(engine, "SELECT id FROM catalogo.area WHERE codigo = 'OTRANS'")
        cambio = leer_cambio(avisos[-1].payload)
        assert cambio == CambioDeIncidencia(None, area, None, categoria)  # type: ignore[arg-type]
    finally:
        await conexion.cerrar()


async def test_una_actualizacion_de_cero_filas_no_avisa(engine: AsyncEngine) -> None:
    conexion = await _abrir(engine)
    try:
        async with transaction(engine, "usuario:prueba") as sql:
            await sql.execute(text("UPDATE chatbot.incidencia_paciente SET activo = false WHERE false"))

        with pytest.raises(TimeoutError):
            await _siguiente(conexion, ESPERA_PARA_SILENCIO)
    finally:
        await conexion.cerrar()


async def test_una_transaccion_revertida_no_avisa(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine, categoria="RECLAMO")
    conexion = await _abrir(engine)
    try:
        async with engine.connect() as sql:
            await sql.execute(text("SELECT set_config('app.actor', 'usuario:prueba', false)"))
            await sql.execute(
                text(
                    "UPDATE chatbot.incidencia_paciente SET categoria_confirmada_en = now() WHERE id = CAST(:id AS uuid)"
                ),
                {"id": caso.id},
            )
            await sql.rollback()

        with pytest.raises(TimeoutError):
            await _siguiente(conexion, ESPERA_PARA_SILENCIO)
    finally:
        await conexion.cerrar()


async def test_si_no_se_puede_conectar_la_apertura_falla() -> None:
    abridor = AbridorDeConexionPostgres("postgresql://u:c@127.0.0.1:1/b", 1)

    with pytest.raises(psycopg.OperationalError):
        await abridor.abrir()
