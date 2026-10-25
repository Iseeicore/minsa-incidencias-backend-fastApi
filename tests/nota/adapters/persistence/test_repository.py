from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.nota.adapters.persistence.repository import SqlCodeGenerator, SqlNotaRepository
from app.nota.adapters.persistence.tables import nota_table
from app.nota.domain.constantes import CONTENIDO_MAX_LENGTH
from tests.helpers.builders import un_codigo, una_nota
from tests.helpers.fakes import AHORA_FIJA

pytestmark = pytest.mark.integration

ESQUEMA_SQL = Path(__file__).parents[4] / "docs" / "esquema" / "nota.sql"
COLUMNAS = """
    SELECT column_name, data_type, is_nullable FROM information_schema.columns
    WHERE table_schema = :esquema AND table_name = 'nota' ORDER BY column_name
"""
RESTRICCIONES = """
    SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
    WHERE conrelid = to_regclass(:esquema || '.nota') ORDER BY conname
"""
FILAS_INVALIDAS = [
    {"codigo": "otro", "titulo": "t", "contenido": "c"},
    {"codigo": "NOTA-\u0660\u0660\u0660\u0660\u0660\u0661", "titulo": "t", "contenido": "c"},
    {"codigo": "NOTA-000001", "titulo": "   ", "contenido": "c"},
    {"codigo": "NOTA-000001", "titulo": "t", "contenido": "x" * (CONTENIDO_MAX_LENGTH + 1)},
]


async def test_guarda_y_recupera_una_nota(engine: AsyncEngine) -> None:
    repositorio = SqlNotaRepository(engine)
    nota = una_nota(5, titulo="Guardada", contenido="Texto")

    await repositorio.save(nota)

    assert await repositorio.find_by_codigo(nota.codigo) == nota


async def test_devuelve_none_si_la_nota_no_existe(engine: AsyncEngine) -> None:
    assert await SqlNotaRepository(engine).find_by_codigo(un_codigo(99)) is None


async def test_los_codigos_siguen_la_secuencia_de_la_base(engine: AsyncEngine) -> None:
    generador = SqlCodeGenerator(engine)

    codigos = [(await generador.next_codigo()).valor for _ in range(2)]

    assert codigos == ["NOTA-000001", "NOTA-000002"]


async def test_el_ddl_versionado_coincide_con_las_tablas_declaradas(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(text("CREATE SCHEMA ddl_versionado"))
        await connection.execute(text("SET LOCAL search_path TO ddl_versionado"))
        await connection.exec_driver_sql(ESQUEMA_SQL.read_text(encoding="utf-8"))
        declaradas = (await connection.execute(text(COLUMNAS), {"esquema": "public"})).all()
        versionadas = (await connection.execute(text(COLUMNAS), {"esquema": "ddl_versionado"})).all()
        restricciones_declaradas = (await connection.execute(text(RESTRICCIONES), {"esquema": "public"})).all()
        restricciones_versionadas = (await connection.execute(text(RESTRICCIONES), {"esquema": "ddl_versionado"})).all()

    assert declaradas
    assert declaradas == versionadas
    assert len(restricciones_declaradas) == 4
    assert restricciones_declaradas == restricciones_versionadas


@pytest.mark.parametrize(
    "fila", FILAS_INVALIDAS, ids=["codigo-ajeno", "digitos-no-ascii", "titulo-en-blanco", "contenido-largo"]
)
async def test_la_base_rechaza_filas_que_incumplen_las_restricciones(engine: AsyncEngine, fila: dict[str, str]) -> None:
    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await connection.execute(insert(nota_table).values(**fila, creada_en=AHORA_FIJA))
