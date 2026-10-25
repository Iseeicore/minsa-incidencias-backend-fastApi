import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.acceso.adapters.persistence.usuarios import SqlUsuarioFinder
from tests.helpers.base import HUELLA_DE_PRUEBA, sembrar_area, sembrar_usuario

pytestmark = pytest.mark.integration


async def test_encuentra_al_usuario_por_su_correo(engine: AsyncEngine) -> None:
    await sembrar_area(engine, 10, "HOSP-01", "Hospital Uno")
    identificador = await sembrar_usuario(engine, "ana@minsa.gob.pe", "GESTOR", 10, nombre="Ana Torres")

    usuario = await SqlUsuarioFinder(engine).buscar_por_correo("ana@minsa.gob.pe")

    assert usuario is not None
    assert (usuario.id, usuario.nombre_completo, usuario.password_hash, usuario.activo) == (
        identificador,
        "Ana Torres",
        HUELLA_DE_PRUEBA,
        True,
    )


async def test_un_correo_desconocido_no_devuelve_usuario(engine: AsyncEngine) -> None:
    assert await SqlUsuarioFinder(engine).buscar_por_correo("nadie@minsa.gob.pe") is None


async def test_un_usuario_desactivado_se_devuelve_marcado_como_inactivo(engine: AsyncEngine) -> None:
    await sembrar_area(engine, 10, "HOSP-01", "Hospital Uno")
    await sembrar_usuario(engine, "baja@minsa.gob.pe", "GESTOR", 10, activo=False)

    usuario = await SqlUsuarioFinder(engine).buscar_por_correo("baja@minsa.gob.pe")

    assert usuario is not None
    assert usuario.activo is False
