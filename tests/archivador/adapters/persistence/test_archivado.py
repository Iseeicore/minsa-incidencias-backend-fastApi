import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.archivador.adapters.persistence.archivado import TOMAR_CANDADO, SqlArchivadoRepositorio
from app.archivador.application.archivar_incidencias import ArchivarIncidencias
from app.constants.archivado import CANDADO_DEL_ARCHIVADOR
from tests.helpers.base import consultar
from tests.helpers.casos import sembrar_caso
from tests.helpers.registro_en_memoria import RegistroEnMemoria

pytestmark = pytest.mark.integration

LOTE_QUE_ALCANZA_PARA_TODA_LA_BASE = 1_000_000
HORAS_POR_DIA = 24


async def _estado(engine: AsyncEngine, incidencia_id: str) -> str:
    [(estado,)] = await consultar(
        engine,
        "SELECT e.codigo FROM chatbot.incidencia_paciente i"
        " JOIN catalogo.estado_incidencia e ON e.id = i.estado_incidencia_id WHERE i.id = CAST(:id AS uuid)",
        id=incidencia_id,
    )
    return str(estado)


def _archivador(engine: AsyncEngine) -> ArchivarIncidencias:
    return ArchivarIncidencias(
        SqlArchivadoRepositorio(engine),
        RegistroEnMemoria(),
        vigencia_dias=3,
        lote=LOTE_QUE_ALCANZA_PARA_TODA_LA_BASE,
    )


async def test_archiva_un_reclamo_vencido_pero_nunca_una_denuncia_vencida_ni_un_caso_sin_categoria(
    engine: AsyncEngine,
) -> None:
    reclamo = await sembrar_caso(engine, categoria="RECLAMO", horas_de_edad=50 * HORAS_POR_DIA)
    denuncia = await sembrar_caso(engine, categoria="DENUNCIA_CORRUPCION", horas_de_edad=8 * HORAS_POR_DIA)
    sin_categoria = await sembrar_caso(engine, categoria=None, horas_de_edad=60 * HORAS_POR_DIA)

    resultado = await _archivador(engine).ejecutar()

    assert resultado.abiertas >= 1
    assert await _estado(engine, reclamo.id) == "ARCHIVADO"
    assert await _estado(engine, denuncia.id) == "CLASIFICADO"
    assert await _estado(engine, sin_categoria.id) == "REGISTRADO"


async def test_archiva_lo_resuelto_hace_mas_de_la_vigencia(engine: AsyncEngine) -> None:
    vieja = await sembrar_caso(engine, categoria="RECLAMO", estado="RESUELTO", horas_desde_resolucion=5 * HORAS_POR_DIA)
    reciente = await sembrar_caso(engine, categoria="RECLAMO", estado="RESUELTO", horas_desde_resolucion=1)

    resultado = await _archivador(engine).ejecutar()

    assert resultado.resueltas >= 1
    assert await _estado(engine, vieja.id) == "ARCHIVADO"
    assert await _estado(engine, reciente.id) == "RESUELTO"


async def test_el_lote_limita_cuantos_casos_se_archivan_por_pasada(engine: AsyncEngine) -> None:
    for _ in range(3):
        await sembrar_caso(engine, categoria="RECLAMO", horas_de_edad=50 * HORAS_POR_DIA)
    repositorio = SqlArchivadoRepositorio(engine)

    primera = await repositorio.archivar_vencidas(2)
    segunda = await repositorio.archivar_vencidas(2)
    tercera = await repositorio.archivar_vencidas(2)

    assert (primera, segunda, tercera) == (2, 1, 0)


async def test_si_otro_proceso_tiene_el_candado_no_archiva_nada(engine: AsyncEngine) -> None:
    reclamo = await sembrar_caso(engine, categoria="RECLAMO", horas_de_edad=50 * HORAS_POR_DIA)
    retenido = asyncio.Event()
    liberar = asyncio.Event()

    async def retener_el_candado() -> None:
        async with engine.begin() as conexion:
            await conexion.execute(TOMAR_CANDADO, {"clave": CANDADO_DEL_ARCHIVADOR})
            retenido.set()
            await liberar.wait()

    tarea = asyncio.create_task(retener_el_candado())
    await asyncio.wait_for(retenido.wait(), timeout=5)

    archivadas = await SqlArchivadoRepositorio(engine).archivar_vencidas(10)
    liberar.set()
    await tarea

    assert archivadas == 0
    assert await _estado(engine, reclamo.id) == "CLASIFICADO"
    assert await SqlArchivadoRepositorio(engine).archivar_vencidas(10) == 1
