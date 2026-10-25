import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.adapters.persistence.indicadores import SqlIndicadoresReader
from app.incidencias.domain.consultas import VisibilidadDeIpress, VisibilidadOperativa
from tests.helpers.casos import sembrar_caso, sembrar_establecimiento

pytestmark = pytest.mark.integration

ADMIN = VisibilidadOperativa(("ADMINISTRADOR",), ver_sin_categoria=True, area_id=None)
AVISO_HORAS = 48
HORAS_DE_UNA_SEMANA = 24 * 7


async def test_sin_casos_todos_los_conteos_son_cero_y_no_hay_tiempo_promedio(engine: AsyncEngine) -> None:
    resumen = await SqlIndicadoresReader(engine).resumen(ADMIN, 7, AVISO_HORAS)

    assert (resumen.recibidos, resumen.recibidos_anterior, resumen.pendientes, resumen.resueltos) == (0, 0, 0, 0)
    assert resumen.segundos_promedio_de_resolucion is None
    assert resumen.generado_en.tzinfo is not None


async def test_el_resumen_separa_el_periodo_actual_del_anterior_y_cuenta_los_pendientes(engine: AsyncEngine) -> None:
    await sembrar_caso(engine, horas_de_edad=2)
    await sembrar_caso(engine, categoria=None, horas_de_edad=HORAS_DE_UNA_SEMANA + 24)
    await sembrar_caso(engine, horas_de_edad=HORAS_DE_UNA_SEMANA * 3)

    resumen = await SqlIndicadoresReader(engine).resumen(ADMIN, 7, AVISO_HORAS)

    assert (resumen.recibidos, resumen.recibidos_anterior) == (1, 1)
    assert resumen.pendientes == 3
    assert resumen.sin_clasificar == 1
    assert resumen.por_revisar == 2
    assert (resumen.en_gestion, resumen.sin_tomar, resumen.resueltos) == (0, 0, 0)


async def test_los_vencidos_y_por_vencer_usan_el_plazo_de_la_categoria(engine: AsyncEngine) -> None:
    await sembrar_caso(engine, categoria="QUEJA", horas_de_edad=24 * 60)
    await sembrar_caso(engine, categoria="QUEJA", horas_de_edad=2)

    resumen = await SqlIndicadoresReader(engine).resumen(ADMIN, 7, AVISO_HORAS)

    assert resumen.vencidos == 1
    assert resumen.por_vencer == 0


async def test_los_resueltos_traen_el_periodo_anterior_y_el_tiempo_promedio_de_resolucion(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 101)
    await sembrar_caso(engine, establecimiento=sitio, estado="RESUELTO", horas_de_edad=5, horas_desde_resolucion=1)

    resumen = await SqlIndicadoresReader(engine).resumen(ADMIN, 7, AVISO_HORAS)

    assert resumen.resueltos == 1
    assert resumen.resueltos_anterior == 0
    assert resumen.segundos_promedio_de_resolucion == pytest.approx(4 * 3600, abs=5)


async def test_las_correcciones_a_corrupcion_se_cuentan_por_periodo(engine: AsyncEngine) -> None:
    await sembrar_caso(engine, categoria="QUEJA", revision="corregida", corregida_a="DENUNCIA_CORRUPCION")

    resumen = await SqlIndicadoresReader(engine).resumen(ADMIN, 7, AVISO_HORAS)

    assert resumen.corregidas_a_corrupcion == 1
    assert resumen.corregidas_a_corrupcion_anterior == 0


async def test_la_distribucion_agrupa_por_estado_y_categoria(engine: AsyncEngine) -> None:
    await sembrar_caso(engine, categoria="QUEJA")
    await sembrar_caso(engine, categoria="QUEJA")
    await sembrar_caso(engine, categoria=None)

    filas = await SqlIndicadoresReader(engine).distribucion(ADMIN)

    cantidades = {(fila.estado, fila.categoria): fila.cantidad for fila in filas}
    assert cantidades[(EstadoIncidencia.CLASIFICADO, CategoriaIncidencia.QUEJA)] == 2
    assert sum(cantidades.values()) == 3


async def test_la_evolucion_trae_un_dia_por_cada_uno_del_periodo_con_los_conteos_de_hoy(engine: AsyncEngine) -> None:
    await sembrar_caso(engine, horas_de_edad=1)
    await sembrar_caso(engine, horas_de_edad=1)

    dias = await SqlIndicadoresReader(engine).evolucion_diaria(ADMIN, 7)

    assert len(dias) == 7
    assert [dia.dia for dia in dias] == sorted(dia.dia for dia in dias)
    assert all(len(dia.dia) == len("2026-01-01") for dia in dias)
    assert sum(dia.recibidos for dia in dias) == 2
    assert sum(dia.resueltos for dia in dias) == 0


async def test_los_indicadores_de_un_establecimiento_solo_cuentan_sus_casos(engine: AsyncEngine) -> None:
    uno = await sembrar_establecimiento(engine, 102)
    otro = await sembrar_establecimiento(engine, 103)
    await sembrar_caso(engine, establecimiento=uno)
    await sembrar_caso(engine, establecimiento=uno, categoria=None)
    await sembrar_caso(engine, establecimiento=otro)
    lector = SqlIndicadoresReader(engine)

    resumen = await lector.resumen(VisibilidadDeIpress(uno.establecimiento_id), 7, AVISO_HORAS)
    distribucion = await lector.distribucion(VisibilidadDeIpress(uno.establecimiento_id))

    assert resumen.recibidos == 2
    assert sum(fila.cantidad for fila in distribucion) == 2
