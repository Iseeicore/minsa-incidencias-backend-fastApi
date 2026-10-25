import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.incidencias.adapters.persistence.ipress import SqlIpressFinder
from app.incidencias.domain.ipress import ConsultaDeIpress
from app.shared.cursor import PosicionPorNombre
from app.shared.transaction import transaction
from tests.helpers.casos import sembrar_establecimiento

pytestmark = pytest.mark.integration


async def _desactivar(engine: AsyncEngine, establecimiento_id: int) -> None:
    async with transaction(engine, "sistema:prueba-padron") as conexion:
        await conexion.execute(
            text("UPDATE catalogo.establecimiento_salud SET activo = false WHERE id = :id"), {"id": establecimiento_id}
        )


async def test_busca_una_ipress_activa_por_su_codigo_renipress(engine: AsyncEngine) -> None:
    sitio = await sembrar_establecimiento(engine, 101, "Centro de Salud")

    ipress = await SqlIpressFinder(engine).buscar(sitio.codigo_renipress)

    assert ipress is not None
    assert (ipress.establecimiento_id, ipress.codigo, ipress.nombre) == (
        sitio.establecimiento_id,
        sitio.area_codigo,
        sitio.area_nombre,
    )


async def test_una_ipress_que_no_existe_o_esta_inactiva_no_se_encuentra(engine: AsyncEngine) -> None:
    inactiva = await sembrar_establecimiento(engine, 102)
    await _desactivar(engine, inactiva.establecimiento_id)
    lector = SqlIpressFinder(engine)

    assert await lector.buscar(inactiva.codigo_renipress) is None
    assert await lector.buscar("12345678") is None


async def test_lista_las_ipress_activas_por_nombre_y_pagina_con_cursor(engine: AsyncEngine) -> None:
    await sembrar_establecimiento(engine, 103, "Alfa")
    await sembrar_establecimiento(engine, 104, "Beta")
    inactiva = await sembrar_establecimiento(engine, 105, "Gamma")
    await _desactivar(engine, inactiva.establecimiento_id)
    lector = SqlIpressFinder(engine)

    primera = await lector.listar(ConsultaDeIpress(limite=1), 1)
    siguiente = await lector.listar(
        ConsultaDeIpress(limite=1, despues_de=PosicionPorNombre(primera[0].nombre, primera[0].id)), 5
    )

    assert [ipress.nombre for ipress in primera] == ["Alfa 9000103"]
    assert [ipress.nombre for ipress in siguiente] == ["Beta 9000104"]
    assert (primera[0].categoria, primera[0].nivel_atencion) == ("II-1", "II")


async def test_la_busqueda_por_texto_acepta_nombre_sin_tilde_y_codigo_renipress(engine: AsyncEngine) -> None:
    uno = await sembrar_establecimiento(engine, 106, "Hospital Ñandú")
    await sembrar_establecimiento(engine, 107, "Posta Rural")
    lector = SqlIpressFinder(engine)

    por_nombre = await lector.listar(ConsultaDeIpress(limite=10, texto="nandu"), 10)
    por_codigo = await lector.listar(ConsultaDeIpress(limite=10, texto=uno.codigo_renipress), 10)
    sin_coincidencias = await lector.listar(ConsultaDeIpress(limite=10, texto="zzz"), 10)

    assert [ipress.id for ipress in por_nombre] == [uno.area_id]
    assert [ipress.id for ipress in por_codigo] == [uno.area_id]
    assert sin_coincidencias == []
