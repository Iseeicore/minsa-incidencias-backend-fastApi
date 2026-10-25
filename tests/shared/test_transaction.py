import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.constants.actores import ACTOR_SISTEMA_GESTION
from app.shared.transaction import actor_usuario_interno, transaction

pytestmark = pytest.mark.integration

ACTOR_ACTUAL = text("SELECT current_setting('app.actor', true)")


def test_el_actor_de_un_usuario_interno_lleva_su_correo() -> None:
    assert actor_usuario_interno("ana@minsa.gob.pe") == "usuario:ana@minsa.gob.pe"


async def test_dentro_de_la_transaccion_la_base_ve_al_actor(engine: AsyncEngine) -> None:
    async with transaction(engine, ACTOR_SISTEMA_GESTION) as conexion:
        actor = (await conexion.execute(ACTOR_ACTUAL)).scalar_one()

    assert actor == "sistema:gestion"


async def test_el_actor_no_se_filtra_a_la_siguiente_conexion(engine: AsyncEngine) -> None:
    async with transaction(engine, actor_usuario_interno("ana@minsa.gob.pe")):
        pass

    async with engine.connect() as conexion:
        actor = (await conexion.execute(ACTOR_ACTUAL)).scalar_one()

    assert not actor


async def test_un_error_dentro_de_la_transaccion_deshace_los_cambios(engine: AsyncEngine) -> None:
    mensaje = "falla de negocio"

    async def fallar() -> None:
        async with transaction(engine, ACTOR_SISTEMA_GESTION) as conexion:
            await conexion.execute(text("CREATE TABLE prueba_tx_real (id int)"))
            raise RuntimeError(mensaje)

    with pytest.raises(RuntimeError, match=mensaje):
        await fallar()

    async with engine.connect() as conexion:
        existe = (await conexion.execute(text("SELECT to_regclass('prueba_tx_real')"))).scalar_one()

    assert existe is None
