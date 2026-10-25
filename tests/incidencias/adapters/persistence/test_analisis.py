import json

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.incidencias.adapters.persistence.analisis import SqlAnalisisReader
from app.shared.transaction import transaction
from tests.helpers.casos import sembrar_caso, sembrar_establecimiento

pytestmark = pytest.mark.integration

SENALES = {"senales": [{"frase": "me pidió plata", "tipo": "FUERTE", "peso": 3}], "explicacion": "Pedido de dinero."}


async def _guardar_analisis(engine: AsyncEngine, incidencia_id: str, area_id: int | None = None) -> None:
    async with transaction(engine, "sistema:clasificador") as conexion:
        await conexion.execute(
            text(
                "INSERT INTO chatbot.incidencia_analisis"
                " (incidencia_paciente_id, version_reglas, puntaje, senales, cargo_mencionado, nombre_mencionado,"
                "  area_mencionada_id)"
                " VALUES (CAST(:id AS uuid), 'reglas-corrupcion-v1.3', 5, CAST(:senales AS jsonb), 'jefa', 'Ana',"
                "  :area_id)"
            ),
            {"id": incidencia_id, "senales": json.dumps(SENALES), "area_id": area_id},
        )


async def test_lee_el_analisis_guardado_con_los_datos_de_la_clasificacion_del_caso(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 101)
    caso = await sembrar_caso(engine, categoria="DENUNCIA_CORRUPCION", confianza=82)
    await _guardar_analisis(engine, caso.id, sitio.area_id)

    fila = await SqlAnalisisReader(engine).buscar(caso.id)

    assert fila is not None
    assert (fila.version_reglas, fila.puntaje, fila.cargo_mencionado, fila.nombre_mencionado) == (
        "reglas-corrupcion-v1.3",
        5,
        "jefa",
        "Ana",
    )
    assert fila.senales == SENALES
    assert (fila.area_mencionada_codigo, fila.area_mencionada_nombre) == (sitio.area_codigo, sitio.area_nombre)
    assert (fila.categoria_ia, fila.confianza_ia) == (CategoriaIncidencia.DENUNCIA_CORRUPCION, 82.0)
    assert fila.version_clasificador == "v-prueba"
    assert fila.fecha_analisis.tzinfo is not None


async def test_un_analisis_sin_area_mencionada_deja_esos_campos_nulos(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine, categoria=None)
    await _guardar_analisis(engine, caso.id)

    fila = await SqlAnalisisReader(engine).buscar(caso.id)

    assert fila is not None
    assert (fila.area_mencionada_codigo, fila.area_mencionada_nombre, fila.categoria_ia) == (None, None, None)


async def test_un_caso_sin_analisis_no_devuelve_fila(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine)

    assert await SqlAnalisisReader(engine).buscar(caso.id) is None
