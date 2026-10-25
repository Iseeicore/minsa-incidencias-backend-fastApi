from dataclasses import dataclass
from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.filtro_corrupcion.adapters.persistence import sentencias_del_clasificador
from app.filtro_corrupcion.adapters.persistence.clasificador import SqlAlarmaReader, SqlClasificadorUnitOfWork
from app.filtro_corrupcion.application.clasificar_incidencias import (
    ClasificadorIncidencias,
    ColaVacia,
    FalloDeClasificacion,
    IncidenciaClasificada,
    consultar_alarma_sin_clasificar,
    vaciar_cola,
)
from tests.helpers.base import consultar
from tests.helpers.casos import sembrar_caso, sembrar_establecimiento

pytestmark = pytest.mark.integration

TEXTO_COBRO = "El director del hospital me pidió plata para atenderme"
TEXTO_NEUTRO = "Quiero saber a qué hora abre la farmacia del hospital por las tardes"
TEXTO_QUEJA = "El personal fue grosero y prepotente conmigo"
TEXTO_ZONA_GRIS = "El director del Hospital Dos de Mayo pide cosas a los pacientes que pagaron en caja"


@dataclass(frozen=True, slots=True)
class EstadoDelCaso:
    categoria_ia: str | None
    categoria: str | None
    estado: str
    confianza: float | None
    version: str | None
    area_destino: str | None
    analisis: int


@dataclass(frozen=True, slots=True)
class AnalisisGuardado:
    version_reglas: str
    puntaje: int
    senales: dict[str, Any]
    usuario: str
    cargo: str | None


def _clasificador(engine: AsyncEngine, **opciones: Any) -> ClasificadorIncidencias:  # noqa: ANN401
    return ClasificadorIncidencias(SqlClasificadorUnitOfWork(engine), **opciones)


async def _estado(engine: AsyncEngine, incidencia_id: str) -> EstadoDelCaso:
    [fila] = await consultar(
        engine,
        "SELECT cia.codigo, cat.codigo, e.codigo, CAST(i.categoria_confianza AS float8), i.version_clasificador,"
        " a.codigo, (SELECT CAST(count(*) AS int) FROM chatbot.incidencia_analisis x"
        " WHERE x.incidencia_paciente_id = i.id)"
        " FROM chatbot.incidencia_paciente i"
        " JOIN catalogo.estado_incidencia e ON e.id = i.estado_incidencia_id"
        " LEFT JOIN catalogo.categoria_incidencia cia ON cia.id = i.categoria_ia_id"
        " LEFT JOIN catalogo.categoria_incidencia cat ON cat.id = i.categoria_id"
        " LEFT JOIN catalogo.area a ON a.id = i.area_destino_id"
        " WHERE i.id = CAST(:id AS uuid)",
        id=incidencia_id,
    )
    return EstadoDelCaso(*cast("tuple[Any, ...]", fila))


async def _analisis(engine: AsyncEngine, incidencia_id: str) -> AnalisisGuardado:
    [fila] = await consultar(
        engine,
        "SELECT version_reglas, CAST(puntaje AS int), senales, usuario_creacion, cargo_mencionado"
        " FROM chatbot.incidencia_analisis WHERE incidencia_paciente_id = CAST(:id AS uuid)",
        id=incidencia_id,
    )
    return AnalisisGuardado(*cast("tuple[Any, ...]", fila))


async def test_una_corrupcion_se_escribe_como_denuncia_y_la_base_la_destina_a_otrans(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 101)
    caso = await sembrar_caso(engine, categoria=None, establecimiento=sitio, marcador=TEXTO_COBRO)
    assert (await _estado(engine, caso.id)).estado == "REGISTRADO"

    salida = await _clasificador(engine).clasificar_siguiente()

    assert isinstance(salida, IncidenciaClasificada)
    assert (salida.codigo, salida.categoria, salida.motivo) == (
        caso.codigo,
        CategoriaIncidencia.DENUNCIA_CORRUPCION,
        MotivoDeEscritura.REGLAS,
    )
    estado = await _estado(engine, caso.id)
    assert (estado.categoria_ia, estado.categoria, estado.estado) == (
        "DENUNCIA_CORRUPCION",
        "DENUNCIA_CORRUPCION",
        "CLASIFICADO",
    )
    assert (estado.area_destino, estado.analisis) == ("OTRANS", 1)
    assert estado.confianza is not None
    assert 0 < estado.confianza <= 95
    assert estado.version is not None
    assert estado.version.endswith("+coincidencias-v1")
    analisis = await _analisis(engine, caso.id)
    assert (analisis.version_reglas, analisis.usuario) == ("reglas-corrupcion-v1.3", "sistema:clasificador")
    assert analisis.puntaje > 0
    assert analisis.cargo
    assert analisis.senales["decision"]["motivo"] == "REGLAS"
    assert analisis.senales["normas"]["etiqueta"] == "Referencia orientativa; la califica OTRANS."
    assert "ANEXO_C-III-b" in [cita["fragmentoId"] for cita in analisis.senales["normas"]["citas"]]
    assert analisis.senales["modelo"]["variante"] is None


async def test_una_queja_se_escribe_tal_cual_y_la_base_la_destina_al_establecimiento_de_origen(
    engine: AsyncEngine,
) -> None:
    sitio = await sembrar_establecimiento(engine, 102)
    caso = await sembrar_caso(engine, categoria=None, establecimiento=sitio, marcador=TEXTO_QUEJA)

    await _clasificador(engine).clasificar_siguiente()

    estado = await _estado(engine, caso.id)
    assert (estado.categoria_ia, estado.estado, estado.area_destino) == ("QUEJA", "CLASIFICADO", sitio.area_codigo)
    assert (await _analisis(engine, caso.id)).senales["decision"]["motivo"] == "SIN_CORRUPCION"


async def test_la_duda_de_corrupcion_tambien_va_a_otrans_con_confianza_de_a_lo_mas_55(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine, categoria=None, marcador=TEXTO_ZONA_GRIS)

    await _clasificador(engine).clasificar_siguiente()

    estado = await _estado(engine, caso.id)
    assert (estado.categoria_ia, estado.area_destino) == ("DENUNCIA_CORRUPCION", "OTRANS")
    assert estado.confianza is not None
    assert estado.confianza <= 55
    assert (await _analisis(engine, caso.id)).senales["decision"]["motivo"] == "DUDA_SIN_MODELO"


async def test_reintentar_no_duplica_la_segunda_pasada_no_encuentra_casos(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine, categoria=None, marcador=TEXTO_COBRO)
    clasificador = _clasificador(engine)

    assert (await vaciar_cola(clasificador)).clasificadas == 1
    assert await clasificador.clasificar_siguiente() == ColaVacia()
    assert (await vaciar_cola(clasificador)).clasificadas == 0
    assert (await _estado(engine, caso.id)).analisis == 1


async def test_un_caso_que_ya_tiene_categoria_de_la_ia_no_se_vuelve_a_tomar(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine, categoria="OTRO", confianza=61)

    assert (await vaciar_cola(_clasificador(engine))).clasificadas == 0
    estado = await _estado(engine, caso.id)
    assert (estado.categoria_ia, estado.confianza, estado.analisis) == ("OTRO", 61.0, 0)


async def test_la_cola_limitada_a_ciertos_casos_no_toca_los_demas(engine: AsyncEngine) -> None:
    mio = await sembrar_caso(engine, categoria=None, marcador=TEXTO_NEUTRO)
    ajeno = await sembrar_caso(engine, categoria=None, marcador=TEXTO_NEUTRO)

    resumen = await vaciar_cola(_clasificador(engine, solo_casos=(mio.id,)))

    assert resumen.clasificadas == 1
    assert (await _estado(engine, mio.id)).categoria_ia == "RECLAMO"
    assert (await _estado(engine, ajeno.id)).categoria_ia is None


async def test_un_error_de_la_base_a_mitad_de_la_escritura_revierte_todo_y_el_siguiente_intento_funciona(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    caso = await sembrar_caso(engine, categoria=None, marcador=TEXTO_COBRO)
    clasificador = _clasificador(engine)
    original = sentencias_del_clasificador.ACTUALIZAR_CATEGORIA
    monkeypatch.setattr(
        sentencias_del_clasificador,
        "ACTUALIZAR_CATEGORIA",
        text("UPDATE chatbot.incidencia_paciente SET categoria_ia_id_inexistente = 1"),
    )

    salida = await clasificador.clasificar_siguiente()

    assert salida == FalloDeClasificacion(caso.id, caso.codigo, 1, "42703", abandonado=False)
    estado = await _estado(engine, caso.id)
    assert (estado.categoria_ia, estado.estado, estado.analisis) == (None, "REGISTRADO", 0)
    monkeypatch.setattr(sentencias_del_clasificador, "ACTUALIZAR_CATEGORIA", original)
    assert isinstance(await clasificador.clasificar_siguiente(), IncidenciaClasificada)
    estado = await _estado(engine, caso.id)
    assert (estado.categoria_ia, estado.analisis) == ("DENUNCIA_CORRUPCION", 1)


def test_la_cola_se_toma_con_skip_locked_del_mas_antiguo_al_mas_nuevo_solo_casos_abiertos_sin_categoria() -> None:
    sql = str(sentencias_del_clasificador.SIGUIENTE_PENDIENTE)

    assert "FOR UPDATE OF i SKIP LOCKED" in sql
    assert "s.codigo = :estado" in sql
    assert "i.categoria_ia_id IS NULL" in sql
    assert "ORDER BY i.fecha_creacion" in sql


async def test_dos_trabajadores_a_la_vez_no_toman_el_mismo_caso(engine: AsyncEngine) -> None:
    primero = await sembrar_caso(engine, categoria=None, marcador=TEXTO_NEUTRO)
    segundo = await sembrar_caso(engine, categoria=None, marcador=TEXTO_NEUTRO)
    unidad = SqlClasificadorUnitOfWork(engine)

    async with unidad.begin("sistema:clasificador") as uno, unidad.begin("sistema:clasificador") as otro:
        tomado_por_uno = await uno.siguiente_pendiente((), None)
        tomado_por_otro = await otro.siguiente_pendiente((), None)

    assert tomado_por_uno is not None
    assert tomado_por_otro is not None
    assert {tomado_por_uno.id, tomado_por_otro.id} == {primero.id, segundo.id}


async def test_la_alarma_se_enciende_con_un_caso_viejo_sin_clasificar_y_se_apaga_al_clasificarlo(
    engine: AsyncEngine,
) -> None:
    viejo = await sembrar_caso(engine, categoria=None, marcador=TEXTO_NEUTRO, horas_de_edad=1)
    reciente = await sembrar_caso(engine, categoria=None, marcador=TEXTO_NEUTRO)
    lector = SqlAlarmaReader(engine)

    alarma = await consultar_alarma_sin_clasificar(lector)

    assert alarma.activa is True
    assert viejo.codigo in alarma.codigos
    assert reciente.codigo not in alarma.codigos
    assert alarma.minutos_del_mas_antiguo is not None
    assert alarma.minutos_del_mas_antiguo >= 59

    await vaciar_cola(_clasificador(engine))

    despues = await consultar_alarma_sin_clasificar(lector)
    assert viejo.codigo not in despues.codigos
    assert despues.activa is False


async def test_el_actor_de_la_clasificacion_queda_en_la_auditoria_de_la_base(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine, categoria=None, marcador=TEXTO_COBRO)

    await _clasificador(engine).clasificar_siguiente()

    [(actor,)] = await consultar(
        engine,
        "SELECT a.actor FROM chatbot.incidencia_paciente_auditoria a"
        " WHERE a.incidencia_paciente_id = CAST(:id AS uuid) AND a.operacion = 'ACTUALIZACION'"
        " ORDER BY a.fecha_hora DESC LIMIT 1",
        id=caso.id,
    )
    assert actor == "sistema:clasificador"


async def test_el_area_mencionada_se_busca_por_codigo_sin_distinguir_mayusculas(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 103)
    unidad = SqlClasificadorUnitOfWork(engine)

    async with unidad.begin("sistema:clasificador") as transaccion:
        area = await transaccion.area_mencionada(sitio.area_codigo.lower())
        inexistente = await transaccion.area_mencionada("no-existe")

    assert (area, inexistente) == (sitio.area_id, None)
