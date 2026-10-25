from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.situacion_derivacion import SituacionDerivacion
from app.enums.tipo_area import TipoArea
from app.incidencias.adapters.persistence.derivaciones import SqlDerivacionReader
from app.incidencias.adapters.persistence.escritura import SqlIncidenciaUnitOfWork
from app.incidencias.adapters.persistence.repository import SqlIncidenciaReader
from app.incidencias.application.acciones import Archivar
from app.incidencias.application.acciones_de_derivacion import Corregir
from app.incidencias.application.ejecutar_accion import EjecutarAccion
from app.incidencias.domain.consultas import FiltrosCasos, VisibilidadDeDerivaciones, VisibilidadDeIpress
from app.incidencias.domain.cursores import PosicionDeDerivacion
from app.incidencias.domain.derivaciones import ConsultaDeDerivaciones, FiltrosDeDerivaciones
from app.incidencias.domain.plazo import PlazosConfigurados
from tests.helpers.base import sembrar_usuario
from tests.helpers.builders import un_area_de_sesion, una_sesion
from tests.helpers.casos import CasoSembrado, EstablecimientoSembrado, sembrar_caso, sembrar_establecimiento

pytestmark = pytest.mark.integration

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
AREA_OTRANS = 1
CORREO_OTRANS = "otrans-prueba@minsa.gob.pe"
TEXTO = "Se devuelve al establecimiento porque corresponde a un reclamo."
OTRANS = una_sesion(
    correo=CORREO_OTRANS, roles=("OTRANS",), area=un_area_de_sesion(id=AREA_OTRANS, tipo=TipoArea.OTRANS)
)
ADMIN = una_sesion(correo="admin-prueba@minsa.gob.pe", roles=("ADMINISTRADOR",))
TODO = FiltrosDeDerivaciones()


async def _ejecutar(engine: AsyncEngine, sesion: object, codigo: str, accion: object) -> None:
    ejecutor = EjecutarAccion(SqlIncidenciaUnitOfWork(engine), SqlIncidenciaReader(engine), PLAZOS)
    await ejecutor.execute(sesion, codigo, accion)  # type: ignore[arg-type]


async def _enviar(
    engine: AsyncEngine,
    sitio: EstablecimientoSembrado,
    categoria: CategoriaIncidencia = CategoriaIncidencia.RECLAMO,
) -> CasoSembrado:
    caso = await sembrar_caso(engine, categoria="DENUNCIA_CORRUPCION", establecimiento=sitio)
    await _ejecutar(engine, OTRANS, caso.codigo, Corregir(categoria, TEXTO))
    return caso


async def _codigos(lector: SqlDerivacionReader, filtros: FiltrosDeDerivaciones = TODO) -> list[str]:
    return [fila.codigo_caso for fila in await lector.listar(ConsultaDeDerivaciones(100, filtros), 100)]


async def test_un_caso_que_otrans_devolvio_al_establecimiento_trae_el_envio_completo(engine: AsyncEngine) -> None:
    await sembrar_usuario(engine, CORREO_OTRANS, "OTRANS", AREA_OTRANS, nombre="Lucía Ramos")
    sitio = await sembrar_establecimiento(engine, 101)
    caso = await _enviar(engine, sitio)

    [fila] = await SqlDerivacionReader(engine).listar(ConsultaDeDerivaciones(10), 11)

    assert fila.codigo_caso == caso.codigo
    assert fila.id.isdigit()
    assert (fila.destino_codigo, fila.destino_nombre, fila.destino_renipress) == (
        sitio.area_codigo,
        sitio.area_nombre,
        sitio.codigo_renipress,
    )
    assert fila.origen_codigo == "OTRANS"
    assert (fila.derivado_por, fila.descripcion) == ("Lucía Ramos", TEXTO)
    assert (fila.categoria, fila.estado) == (CategoriaIncidencia.RECLAMO, EstadoIncidencia.CLASIFICADO)
    assert fila.motivo_archivo is None


async def test_un_envio_de_un_usuario_que_ya_no_existe_no_trae_su_nombre(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 102)
    await _enviar(engine, sitio)

    [fila] = await SqlDerivacionReader(engine).listar(ConsultaDeDerivaciones(10), 11)

    assert fila.derivado_por is None


async def test_un_caso_que_nunca_salio_de_otrans_no_es_una_derivacion(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 103)
    await sembrar_caso(engine, categoria="DENUNCIA_CORRUPCION", establecimiento=sitio)
    await sembrar_caso(engine, categoria="RECLAMO", establecimiento=sitio)

    assert await _codigos(SqlDerivacionReader(engine)) == []


async def test_se_listan_del_envio_mas_reciente_al_mas_antiguo_y_se_pagina_con_cursor(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 104)
    primero = await _enviar(engine, sitio)
    segundo = await _enviar(engine, sitio)
    tercero = await _enviar(engine, sitio)
    lector = SqlDerivacionReader(engine)

    pagina = await lector.listar(ConsultaDeDerivaciones(2), 2)
    ultima = pagina[-1]
    siguiente = await lector.listar(
        ConsultaDeDerivaciones(2, despues_de=PosicionDeDerivacion(ultima.fecha_derivacion, ultima.id)), 2
    )

    assert [fila.codigo_caso for fila in pagina] == [tercero.codigo, segundo.codigo]
    assert [fila.codigo_caso for fila in siguiente] == [primero.codigo]


async def test_los_filtros_de_establecimiento_texto_y_categoria(engine: AsyncEngine) -> None:
    uno = await sembrar_establecimiento(engine, 105)
    otro = await sembrar_establecimiento(engine, 106)
    en_uno = await _enviar(engine, uno, CategoriaIncidencia.QUEJA)
    en_otro = await _enviar(engine, otro, CategoriaIncidencia.RECLAMO)
    lector = SqlDerivacionReader(engine)

    assert await _codigos(lector, FiltrosDeDerivaciones(establecimiento=uno.codigo_renipress)) == [en_uno.codigo]
    assert await _codigos(lector, FiltrosDeDerivaciones(texto=en_otro.codigo[-6:])) == [en_otro.codigo]
    assert await _codigos(lector, FiltrosDeDerivaciones(categoria=CategoriaIncidencia.QUEJA)) == [en_uno.codigo]
    assert await _codigos(lector, FiltrosDeDerivaciones(texto="NO-EXISTE")) == []


async def test_el_rango_de_fechas_usa_el_dia_de_lima_del_envio(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 107)
    caso = await _enviar(engine, sitio)
    hoy = datetime.now(UTC).strftime("%Y-%m-%d")
    lector = SqlDerivacionReader(engine)

    assert await _codigos(lector, FiltrosDeDerivaciones(desde="2000-01-01", hasta="2000-01-02")) == []
    assert await _codigos(lector, FiltrosDeDerivaciones(desde="2000-01-01", hasta="2999-12-31")) == [caso.codigo]
    assert await _codigos(lector, FiltrosDeDerivaciones(desde=hoy)) == [caso.codigo]


async def test_la_situacion_agrupa_los_estados_del_caso_y_los_conteos_la_ignoran(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 108)
    pendiente = await _enviar(engine, sitio)
    archivado = await _enviar(engine, sitio)
    await _ejecutar(engine, ADMIN, archivado.codigo, Archivar(MotivoArchivo.NO_CORRESPONDE, TEXTO))
    lector = SqlDerivacionReader(engine)

    en_pendientes = await _codigos(lector, FiltrosDeDerivaciones(situacion=SituacionDerivacion.PENDIENTE))
    en_archivados = await _codigos(lector, FiltrosDeDerivaciones(situacion=SituacionDerivacion.ARCHIVADO))
    conteos = await lector.contar(FiltrosDeDerivaciones(situacion=SituacionDerivacion.RESUELTO))

    assert en_pendientes == [pendiente.codigo]
    assert en_archivados == [archivado.codigo]
    assert (conteos.todos, conteos.pendientes, conteos.en_gestion, conteos.resueltos, conteos.archivados) == (
        2,
        1,
        0,
        0,
        1,
    )


async def test_el_detalle_de_un_archivado_trae_su_motivo_y_uno_que_no_se_envio_no_existe(
    engine: AsyncEngine,
) -> None:
    sitio = await sembrar_establecimiento(engine, 109)
    caso = await _enviar(engine, sitio)
    sin_enviar = await sembrar_caso(engine, categoria="DENUNCIA_CORRUPCION", establecimiento=sitio)
    await _ejecutar(engine, ADMIN, caso.codigo, Archivar(MotivoArchivo.NO_CORRESPONDE, TEXTO))
    lector = SqlDerivacionReader(engine)

    fila = await lector.buscar_por_codigo(caso.codigo)

    assert fila is not None
    assert (fila.estado, fila.motivo_archivo) == (EstadoIncidencia.ARCHIVADO, MotivoArchivo.NO_CORRESPONDE)
    assert await lector.buscar_por_codigo(sin_enviar.codigo) is None
    assert await lector.buscar_por_codigo("MINSA-2026-999999") is None


async def test_la_visibilidad_del_seguimiento_alcanza_solo_los_casos_enviados(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 110)
    enviado = await _enviar(engine, sitio)
    sin_enviar = await sembrar_caso(engine, categoria="DENUNCIA_CORRUPCION", establecimiento=sitio)
    lector = SqlIncidenciaReader(engine)
    visible = VisibilidadDeDerivaciones()

    assert await lector.buscar_por_codigo(enviado.codigo, visible) is not None
    assert await lector.buscar_por_codigo(sin_enviar.codigo, visible) is None
    assert [caso.codigo for caso in await lector.listar(visible, FiltrosCasos(), 10, None)] == [enviado.codigo]


async def test_la_visibilidad_de_ipress_alcanza_los_casos_del_establecimiento(engine: AsyncEngine) -> None:
    uno = await sembrar_establecimiento(engine, 111)
    otro = await sembrar_establecimiento(engine, 112)
    suyo = await sembrar_caso(engine, establecimiento=uno)
    sin_categoria = await sembrar_caso(engine, categoria=None, establecimiento=uno)
    await sembrar_caso(engine, establecimiento=otro)
    lector = SqlIncidenciaReader(engine)

    codigos = {
        caso.codigo
        for caso in await lector.listar(VisibilidadDeIpress(uno.establecimiento_id), FiltrosCasos(), 10, None)
    }

    assert codigos == {suyo.codigo, sin_categoria.codigo}
