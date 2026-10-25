import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.acceso.adapters.persistence.sesiones import SqlSesionStore
from app.enums.tipo_area import TipoArea
from tests.helpers.base import ACTOR_DE_PRUEBA, consultar, sembrar_area, sembrar_usuario

pytestmark = pytest.mark.integration

IDLE_MINUTES = 30
TOUCH_SECONDS = 60
ABSOLUTE_HOURS = 8


async def _usuario(engine: AsyncEngine, correo: str = "ana@minsa.gob.pe", *, activo: bool = True) -> str:
    await sembrar_area(engine, 10, "HOSP-01", "Hospital Uno")
    return await sembrar_usuario(engine, correo, "GESTOR", 10, nombre="Ana Torres", activo=activo)


async def _retroceder_actividad(engine: AsyncEngine, sesion_id: str, segundos: int) -> None:
    async with engine.begin() as conexion:
        await conexion.execute(text("SET LOCAL session_replication_role = replica"))
        await conexion.execute(
            text(
                "UPDATE gestion.sesion_usuario SET ultima_actividad_en = now() - make_interval(secs => :s)"
                " WHERE id = CAST(:id AS uuid)"
            ),
            {"s": segundos, "id": sesion_id},
        )


async def test_crea_una_sesion_que_vence_a_las_horas_absolutas(engine: AsyncEngine) -> None:
    usuario_id = await _usuario(engine)
    almacen = SqlSesionStore(engine)

    sesion_id = await almacen.crear(ACTOR_DE_PRUEBA, usuario_id, ABSOLUTE_HOURS)

    filas = await consultar(
        engine,
        "SELECT vence_en - now() > make_interval(hours => 7) FROM gestion.sesion_usuario WHERE id = CAST(:id AS uuid)",
        id=sesion_id,
    )
    assert filas == [(True,)]


async def test_una_sesion_vigente_trae_al_usuario_sus_roles_y_su_area(engine: AsyncEngine) -> None:
    usuario_id = await _usuario(engine)
    almacen = SqlSesionStore(engine)
    sesion_id = await almacen.crear(ACTOR_DE_PRUEBA, usuario_id, ABSOLUTE_HOURS)

    vigente = await almacen.buscar_vigente(sesion_id, IDLE_MINUTES, TOUCH_SECONDS)

    assert vigente is not None
    assert (vigente.sesion_id, vigente.usuario_id, vigente.correo, vigente.roles) == (
        sesion_id,
        usuario_id,
        "ana@minsa.gob.pe",
        ("GESTOR",),
    )
    assert vigente.area is not None
    assert (vigente.area.id, vigente.area.codigo, vigente.area.tipo) == (10, "HOSP-01", TipoArea.ESTABLECIMIENTO)
    assert vigente.debe_tocar is False
    assert vigente.vigencia.vence_en > vigente.vigencia.inactiva_en


async def test_una_sesion_con_actividad_vieja_pide_tocarse(engine: AsyncEngine) -> None:
    usuario_id = await _usuario(engine)
    almacen = SqlSesionStore(engine)
    sesion_id = await almacen.crear(ACTOR_DE_PRUEBA, usuario_id, ABSOLUTE_HOURS)
    await _retroceder_actividad(engine, sesion_id, TOUCH_SECONDS * 2)

    vigente = await almacen.buscar_vigente(sesion_id, IDLE_MINUTES, TOUCH_SECONDS)

    assert vigente is not None
    assert vigente.debe_tocar is True


async def test_tocar_la_actividad_renueva_la_ventana_de_inactividad(engine: AsyncEngine) -> None:
    usuario_id = await _usuario(engine)
    almacen = SqlSesionStore(engine)
    sesion_id = await almacen.crear(ACTOR_DE_PRUEBA, usuario_id, ABSOLUTE_HOURS)
    await _retroceder_actividad(engine, sesion_id, TOUCH_SECONDS * 2)

    vigencia = await almacen.tocar_actividad(ACTOR_DE_PRUEBA, sesion_id, IDLE_MINUTES)
    despues = await almacen.buscar_vigente(sesion_id, IDLE_MINUTES, TOUCH_SECONDS)

    assert vigencia is not None
    assert despues is not None
    assert despues.debe_tocar is False


async def test_una_sesion_inactiva_mas_alla_del_limite_ya_no_es_vigente(engine: AsyncEngine) -> None:
    usuario_id = await _usuario(engine)
    almacen = SqlSesionStore(engine)
    sesion_id = await almacen.crear(ACTOR_DE_PRUEBA, usuario_id, ABSOLUTE_HOURS)
    await _retroceder_actividad(engine, sesion_id, (IDLE_MINUTES + 1) * 60)

    assert await almacen.buscar_vigente(sesion_id, IDLE_MINUTES, TOUCH_SECONDS) is None
    assert await almacen.tocar_actividad(ACTOR_DE_PRUEBA, sesion_id, IDLE_MINUTES) is None


async def test_revocar_deja_la_sesion_fuera_de_las_vigentes(engine: AsyncEngine) -> None:
    usuario_id = await _usuario(engine)
    almacen = SqlSesionStore(engine)
    sesion_id = await almacen.crear(ACTOR_DE_PRUEBA, usuario_id, ABSOLUTE_HOURS)
    assert await almacen.buscar_correo_de_sesion_abierta(sesion_id) == "ana@minsa.gob.pe"

    await almacen.revocar(ACTOR_DE_PRUEBA, sesion_id)

    assert await almacen.buscar_vigente(sesion_id, IDLE_MINUTES, TOUCH_SECONDS) is None
    assert await almacen.buscar_correo_de_sesion_abierta(sesion_id) is None


async def test_una_sesion_de_un_usuario_desactivado_no_es_vigente(engine: AsyncEngine) -> None:
    usuario_id = await _usuario(engine)
    almacen = SqlSesionStore(engine)
    sesion_id = await almacen.crear(ACTOR_DE_PRUEBA, usuario_id, ABSOLUTE_HOURS)
    async with engine.begin() as conexion:
        await conexion.execute(text("SELECT set_config('app.actor', 'sistema:prueba', true)"))
        await conexion.execute(
            text(
                "UPDATE gestion.usuario_interno SET activo = false, eliminado_en = now(), eliminado_por = :actor"
                " WHERE id = CAST(:id AS uuid)"
            ),
            {"id": usuario_id, "actor": ACTOR_DE_PRUEBA},
        )

    assert await almacen.buscar_vigente(sesion_id, IDLE_MINUTES, TOUCH_SECONDS) is None


async def test_un_identificador_desconocido_no_devuelve_nada(engine: AsyncEngine) -> None:
    almacen = SqlSesionStore(engine)
    desconocido = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"

    assert await almacen.buscar_vigente(desconocido, IDLE_MINUTES, TOUCH_SECONDS) is None
    assert await almacen.buscar_correo_de_sesion_abierta(desconocido) is None
