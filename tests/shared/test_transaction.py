from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.constants.actores import ACTOR_SISTEMA_GESTION
from app.shared.actor import actor_usuario_interno
from app.shared.transaction import transaction

ACTOR_ACTUAL = text("SELECT current_setting('app.actor', true)")


class ConexionFalsa:
    def __init__(self) -> None:
        self.ejecuciones: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, sentencia: object, parametros: dict[str, Any]) -> None:
        self.ejecuciones.append((str(sentencia), parametros))


class ContextoFalso:
    def __init__(self, conexion: ConexionFalsa) -> None:
        self._conexion = conexion
        self.cerrado_con_error: bool | None = None

    async def __aenter__(self) -> ConexionFalsa:
        return self._conexion

    async def __aexit__(self, tipo: object, valor: object, traza: object) -> None:
        self.cerrado_con_error = tipo is not None


class MotorFalso:
    def __init__(self) -> None:
        self.conexion = ConexionFalsa()
        self.contexto = ContextoFalso(self.conexion)

    def begin(self) -> ContextoFalso:
        return self.contexto


async def test_la_transaccion_fija_el_actor_antes_de_ceder_la_conexion() -> None:
    motor = MotorFalso()

    async with transaction(motor, "usuario:ana@minsa.gob.pe") as conexion:  # type: ignore[arg-type]
        assert cast("object", conexion) is motor.conexion
        assert motor.conexion.ejecuciones == [
            ("SELECT set_config('app.actor', :actor, true)", {"actor": "usuario:ana@minsa.gob.pe"})
        ]

    assert motor.contexto.cerrado_con_error is False


async def test_un_error_dentro_de_la_transaccion_llega_al_motor_para_deshacerla() -> None:
    motor = MotorFalso()
    mensaje = "falla de negocio"

    async def fallar() -> None:
        async with transaction(motor, "sistema:gestion"):  # type: ignore[arg-type]
            raise RuntimeError(mensaje)

    with pytest.raises(RuntimeError, match=mensaje):
        await fallar()

    assert motor.contexto.cerrado_con_error is True


@pytest.mark.integration
async def test_dentro_de_la_transaccion_la_base_ve_al_actor(engine: AsyncEngine) -> None:
    async with transaction(engine, ACTOR_SISTEMA_GESTION) as conexion:
        actor = (await conexion.execute(ACTOR_ACTUAL)).scalar_one()

    assert actor == "sistema:gestion"


@pytest.mark.integration
async def test_el_actor_no_se_filtra_a_la_siguiente_conexion(engine: AsyncEngine) -> None:
    async with transaction(engine, actor_usuario_interno("ana@minsa.gob.pe")):
        pass

    async with engine.connect() as conexion:
        actor = (await conexion.execute(ACTOR_ACTUAL)).scalar_one()

    assert not actor


@pytest.mark.integration
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
