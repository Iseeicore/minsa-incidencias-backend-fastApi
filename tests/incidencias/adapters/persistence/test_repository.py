from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.incidencias.adapters.persistence.repository import SqlIncidenciaReader
from app.incidencias.domain.consultas import FiltrosCasos, VisibilidadOperativa
from app.incidencias.domain.cursores import PosicionDeListado, PosicionPorVencer
from app.shared.acciones_permitidas import reglas_de_avisos
from tests.helpers.casos import IMAGEN_PNG, sembrar_caso, sembrar_establecimiento

pytestmark = pytest.mark.integration

ADMIN = VisibilidadOperativa(("ADMINISTRADOR",), ver_sin_categoria=True, area_id=None)
AREA_OTRANS = 1


def _gestor(area_id: int | None) -> VisibilidadOperativa:
    return VisibilidadOperativa(("GESTOR",), ver_sin_categoria=False, area_id=area_id)


OTRANS = VisibilidadOperativa(("OTRANS",), ver_sin_categoria=False, area_id=AREA_OTRANS)
TODO = FiltrosCasos()


async def _codigos(
    lector: SqlIncidenciaReader, visible: VisibilidadOperativa, filtros: FiltrosCasos = TODO
) -> list[str]:
    return [caso.codigo for caso in await lector.listar(visible, filtros, 100, None)]


async def test_el_administrador_ve_todo_en_orden_de_llegada_descendente_y_pagina_con_cursor(
    engine: AsyncEngine,
) -> None:
    primero = await sembrar_caso(engine, horas_de_edad=3)
    segundo = await sembrar_caso(engine, categoria=None, horas_de_edad=2)
    tercero = await sembrar_caso(engine, horas_de_edad=1)
    lector = SqlIncidenciaReader(engine)

    todos = await lector.listar(ADMIN, TODO, 2, None)
    ultimo = todos[-1]
    siguiente = await lector.listar(ADMIN, TODO, 2, PosicionDeListado(ultimo.fecha_creacion, ultimo.id))

    assert [caso.codigo for caso in todos] == [tercero.codigo, segundo.codigo]
    assert [caso.codigo for caso in siguiente] == [primero.codigo]


async def test_un_gestor_solo_ve_los_casos_de_su_area_y_no_los_sensibles(engine: AsyncEngine) -> None:
    uno = await sembrar_establecimiento(engine, 101)
    otro = await sembrar_establecimiento(engine, 102)
    suyo = await sembrar_caso(engine, establecimiento=uno)
    await sembrar_caso(engine, establecimiento=otro)
    await sembrar_caso(engine, categoria=None, establecimiento=uno)
    lector = SqlIncidenciaReader(engine)

    assert await _codigos(lector, _gestor(uno.area_id)) == [suyo.codigo]
    assert await _codigos(lector, _gestor(None)) == []


async def test_otrans_ve_las_denuncias_de_su_area(engine: AsyncEngine) -> None:
    origen = await sembrar_establecimiento(engine, 103)
    denuncia = await sembrar_caso(engine, categoria="DENUNCIA_CORRUPCION", establecimiento=origen)
    await sembrar_caso(engine, categoria="QUEJA", establecimiento=origen)
    lector = SqlIncidenciaReader(engine)

    assert await _codigos(lector, OTRANS) == [denuncia.codigo]
    assert await _codigos(lector, _gestor(origen.area_id)) == [
        caso.codigo for caso in await lector.listar(_gestor(origen.area_id), TODO, 10, None)
    ]


async def test_el_caso_trae_sus_datos_de_origen_estado_y_plazo(engine: AsyncEngine) -> None:
    origen = await sembrar_establecimiento(engine, 104, "Hospital Origen")
    sembrado = await sembrar_caso(engine, establecimiento=origen, confianza=72, anonimo=False, horas_de_edad=5)

    caso = await SqlIncidenciaReader(engine).buscar_por_codigo(sembrado.codigo, ADMIN)

    assert caso is not None
    assert caso.estado is EstadoIncidencia.CLASIFICADO
    assert (caso.categoria, caso.categoria_ia) == (CategoriaIncidencia.RECLAMO, CategoriaIncidencia.RECLAMO)
    assert caso.confianza_ia == 72
    assert caso.establecimiento_codigo == origen.codigo_renipress
    assert (caso.establecimiento_nivel, caso.establecimiento_categoria) == ("II", "II-1")
    assert caso.area_origen_id == origen.area_id
    assert (caso.es_anonimo, caso.nombre, caso.dni, caso.canal) == (
        False,
        "Luis Alberto Quispe",
        "00001907",
        "WhatsApp",
    )
    assert caso.vence_atencion_en is not None
    assert caso.vence_atencion_en > caso.ahora
    assert caso.revisada is False
    assert caso.sensible is False


async def test_un_caso_ajeno_o_inexistente_no_se_encuentra(engine: AsyncEngine) -> None:
    origen = await sembrar_establecimiento(engine, 105)
    ajeno = await sembrar_establecimiento(engine, 106)
    sembrado = await sembrar_caso(engine, establecimiento=origen)
    lector = SqlIncidenciaReader(engine)

    assert await lector.buscar_por_codigo(sembrado.codigo, _gestor(ajeno.area_id)) is None
    assert await lector.buscar_por_codigo("MINSA-2000-000000", ADMIN) is None
    assert await lector.buscar_por_codigo(sembrado.codigo, _gestor(origen.area_id)) is not None


async def test_los_filtros_por_estado_categoria_sin_categoria_y_establecimiento(engine: AsyncEngine) -> None:
    origen = await sembrar_establecimiento(engine, 107)
    otro = await sembrar_establecimiento(engine, 108)
    clasificado = await sembrar_caso(engine, establecimiento=origen)
    derivado = await sembrar_caso(engine, establecimiento=otro, estado="DERIVADO")
    sin_categoria = await sembrar_caso(engine, categoria=None)
    queja = await sembrar_caso(engine, categoria="QUEJA", establecimiento=origen)
    lector = SqlIncidenciaReader(engine)

    assert await _codigos(lector, ADMIN, FiltrosCasos(estado=EstadoIncidencia.DERIVADO)) == [derivado.codigo]
    assert await _codigos(lector, ADMIN, FiltrosCasos(categoria=CategoriaIncidencia.QUEJA)) == [queja.codigo]
    assert await _codigos(lector, ADMIN, FiltrosCasos(sin_categoria=True)) == [sin_categoria.codigo]
    assert set(await _codigos(lector, ADMIN, FiltrosCasos(establecimiento=origen.codigo_renipress))) == {
        clasificado.codigo,
        queja.codigo,
    }


async def test_el_texto_busca_en_el_codigo_y_el_relato_sin_tratar_los_comodines_como_tales(engine: AsyncEngine) -> None:
    uno = await sembrar_caso(engine, marcador="goteras en el techo")
    dos = await sembrar_caso(engine, marcador="100% de descuento_total")
    lector = SqlIncidenciaReader(engine)

    assert await _codigos(lector, ADMIN, FiltrosCasos(texto="GOTERAS")) == [uno.codigo]
    assert await _codigos(lector, ADMIN, FiltrosCasos(texto=uno.codigo)) == [uno.codigo]
    assert await _codigos(lector, ADMIN, FiltrosCasos(texto="100%")) == [dos.codigo]
    assert await _codigos(lector, ADMIN, FiltrosCasos(texto="descuento_total")) == [dos.codigo]
    assert await _codigos(lector, ADMIN, FiltrosCasos(texto="%")) == [dos.codigo]


async def test_el_rango_de_fechas_usa_el_dia_de_lima(engine: AsyncEngine) -> None:
    dentro = await sembrar_caso(engine, creado_en=datetime(2026, 3, 10, 4, 59, tzinfo=UTC))
    limite_inferior = await sembrar_caso(engine, creado_en=datetime(2026, 3, 10, 5, 0, tzinfo=UTC))
    fuera = await sembrar_caso(engine, creado_en=datetime(2026, 3, 12, 5, 0, tzinfo=UTC))
    lector = SqlIncidenciaReader(engine)

    solo_el_10 = await _codigos(lector, ADMIN, FiltrosCasos(desde="2026-03-10", hasta="2026-03-10"))
    desde_el_9 = await _codigos(lector, ADMIN, FiltrosCasos(desde="2026-03-09", hasta="2026-03-11"))

    assert solo_el_10 == [limite_inferior.codigo]
    assert set(desde_el_9) == {dentro.codigo, limite_inferior.codigo}
    assert fuera.codigo not in desde_el_9


async def test_el_motivo_de_archivo_filtra_los_archivados(engine: AsyncEngine) -> None:
    origen = await sembrar_establecimiento(engine, 109)
    archivado = await sembrar_caso(engine, establecimiento=origen, archivar_motivo="DATOS_INSUFICIENTES")
    await sembrar_caso(engine, establecimiento=origen)
    lector = SqlIncidenciaReader(engine)

    codigos = await _codigos(lector, ADMIN, FiltrosCasos(motivo_archivo=MotivoArchivo.DATOS_INSUFICIENTES))
    caso = await lector.buscar_por_codigo(archivado.codigo, ADMIN)

    assert codigos == [archivado.codigo]
    assert caso is not None
    assert (caso.estado, caso.motivo_archivo) == (EstadoIncidencia.ARCHIVADO, MotivoArchivo.DATOS_INSUFICIENTES)
    assert caso.archivo_detalle
    assert caso.archivado_en is not None


async def test_los_conteos_se_acotan_y_se_separan_por_estado(engine: AsyncEngine) -> None:
    origen = await sembrar_establecimiento(engine, 110)
    for _ in range(3):
        await sembrar_caso(engine, establecimiento=origen)
    await sembrar_caso(engine, establecimiento=origen, estado="EN_GESTION")
    lector = SqlIncidenciaReader(engine)

    por_estado = await lector.contar_por_estado(ADMIN, TODO, 1000)
    acotado = await lector.contar_acotado(ADMIN, FiltrosCasos(estado=EstadoIncidencia.CLASIFICADO), 1000)
    con_tope = await lector.contar_por_estado(ADMIN, TODO, 2)

    assert por_estado[EstadoIncidencia.CLASIFICADO] == 3
    assert por_estado[EstadoIncidencia.EN_GESTION] == 1
    assert acotado == 3
    assert con_tope[EstadoIncidencia.CLASIFICADO] == 3
    assert max(con_tope.values()) <= 3


async def test_las_evidencias_dicen_si_su_contenido_se_puede_entregar(engine: AsyncEngine) -> None:
    sembrado = await sembrar_caso(engine, rutas_de_evidencias=[IMAGEN_PNG, "rutas-privadas/archivo.jpg"])
    lector = SqlIncidenciaReader(engine)

    evidencias = await lector.evidencias(sembrado.id)
    ruta = await lector.ruta_de_evidencia(sembrado.id, sembrado.evidencias[0])
    ajena = await lector.ruta_de_evidencia(sembrado.id, "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69")

    assert [evidencia.contenido_disponible for evidencia in evidencias] == [True, False]
    assert [evidencia.tipo for evidencia in evidencias] == ["IMAGEN", "IMAGEN"]
    assert evidencias[0].tipo_nombre == "Imagen"
    assert ruta == IMAGEN_PNG
    assert ajena is None


async def test_el_historial_cuenta_el_registro_la_clasificacion_y_la_derivacion(engine: AsyncEngine) -> None:
    origen = await sembrar_establecimiento(engine, 111)
    sembrado = await sembrar_caso(engine, establecimiento=origen, estado="DERIVADO")

    historial = await SqlIncidenciaReader(engine).historial(sembrado.id)

    assert historial[0].operacion == "CREACION"
    assert any(
        fila.ia and fila.categoria_ia is CategoriaIncidencia.RECLAMO and fila.version == "v-prueba"
        for fila in historial
    )
    derivada = next(fila for fila in historial if fila.estado_nuevo is EstadoIncidencia.DERIVADO)
    assert derivada.actor == "operador:prueba"
    assert any(fila.area_despues == origen.area_nombre for fila in historial)


async def test_los_casos_por_vencer_y_vencidos_se_cuentan_y_se_listan_por_vencimiento(engine: AsyncEngine) -> None:
    origen = await sembrar_establecimiento(engine, 112)
    vencido = await sembrar_caso(engine, establecimiento=origen, horas_de_edad=24 * 120)
    reciente = await sembrar_caso(engine, establecimiento=origen, horas_de_edad=2)
    lector = SqlIncidenciaReader(engine)
    pendientes = reglas_de_avisos(["ADMINISTRADOR"])

    conteo = await lector.contar_por_vencer(ADMIN, 48, pendientes)
    lista = await lector.listar_por_vencer(ADMIN, 48, 10, pendientes)

    assert (conteo.total, conteo.vencidos) == (1, 1)
    assert [caso.codigo for caso in lista] == [vencido.codigo]
    assert reciente.codigo not in [caso.codigo for caso in lista]


async def test_sin_reglas_pendientes_la_campana_queda_vacia(engine: AsyncEngine) -> None:
    origen = await sembrar_establecimiento(engine, 113)
    await sembrar_caso(engine, establecimiento=origen, horas_de_edad=24 * 120)
    lector = SqlIncidenciaReader(engine)

    conteo = await lector.contar_por_vencer(ADMIN, 48, ())
    lista = await lector.listar_por_vencer(ADMIN, 48, 10, ())

    assert (conteo.total, conteo.vencidos) == (0, 0)
    assert lista == []


async def test_el_filtro_de_plazo_lista_solo_los_que_vencen_pronto_y_pagina_por_vencimiento(
    engine: AsyncEngine,
) -> None:
    origen = await sembrar_establecimiento(engine, 114)
    casos = [await sembrar_caso(engine, establecimiento=origen, horas_de_edad=24 * 41 + indice) for indice in range(3)]
    await sembrar_caso(engine, establecimiento=origen, horas_de_edad=2)
    lector = SqlIncidenciaReader(engine)
    filtros = FiltrosCasos(aviso_horas=24 * 30)

    todos = await lector.listar_proximos_a_vencer(ADMIN, filtros, 10, None)
    primera = await lector.listar_proximos_a_vencer(ADMIN, filtros, 2, None)
    ultimo = primera[-1]
    segunda = await lector.listar_proximos_a_vencer(
        ADMIN, filtros, 2, PosicionPorVencer(ultimo.vence_atencion_en or ultimo.fecha_creacion, ultimo.id)
    )

    assert {caso.codigo for caso in todos} <= {caso.codigo for caso in casos}
    assert [caso.codigo for caso in primera + segunda] == [caso.codigo for caso in todos]
