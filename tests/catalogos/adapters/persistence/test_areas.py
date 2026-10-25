import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.catalogos.adapters.persistence.areas import SqlAreaFinder
from app.catalogos.domain.area_listada import FiltrosDeAreas
from app.enums.tipo_area import TipoArea
from app.shared.cursor import PosicionPorNombre
from app.shared.transaction import transaction
from tests.helpers.base import ACTOR_DE_PRUEBA, sembrar_area

pytestmark = pytest.mark.integration

OTRANS_SEMBRADA = 1


async def _con_establecimiento(engine: AsyncEngine, area_id: int, renipress: str, nombre: str) -> None:
    async with transaction(engine, ACTOR_DE_PRUEBA) as conexion:
        await conexion.execute(
            text(
                "INSERT INTO catalogo.establecimiento_salud (id, codigo_renipress, nombre, categoria, area_id)"
                " VALUES (:id, :renipress, :nombre, 'II-1', :area_id)"
            ),
            {"id": area_id, "renipress": renipress, "nombre": nombre, "area_id": area_id},
        )


async def _escenario(engine: AsyncEngine) -> None:
    await sembrar_area(engine, 10, "HOSP-01", "Hospital Ñandú")
    await sembrar_area(engine, 11, "HOSP-02", "Clínica Central")
    await _con_establecimiento(engine, 10, "1234", "Hospital Ñandú")


async def test_lista_las_areas_activas_ordenadas_por_nombre_con_su_establecimiento(engine: AsyncEngine) -> None:
    await _escenario(engine)

    areas = await SqlAreaFinder(engine).listar(FiltrosDeAreas(), 10, None)

    assert [area.codigo for area in areas] == ["HOSP-02", "HOSP-01", "OTRANS"]
    con_establecimiento = next(area for area in areas if area.codigo == "HOSP-01")
    assert con_establecimiento.establecimiento is not None
    assert (con_establecimiento.establecimiento.codigo_renipress, con_establecimiento.establecimiento.categoria) == (
        "1234",
        "II-1",
    )
    assert areas[0].establecimiento is None
    assert areas[2].tipo_area is TipoArea.OTRANS


async def test_filtra_por_tipo(engine: AsyncEngine) -> None:
    await _escenario(engine)

    areas = await SqlAreaFinder(engine).listar(FiltrosDeAreas(tipo=TipoArea.OTRANS), 10, None)

    assert [area.id for area in areas] == [OTRANS_SEMBRADA]


async def test_restringe_a_un_area_y_sin_area_no_devuelve_nada(engine: AsyncEngine) -> None:
    await _escenario(engine)
    buscador = SqlAreaFinder(engine)

    propia = await buscador.listar(FiltrosDeAreas(solo_area_id=11, restringir_a_un_area=True), 10, None)
    ninguna = await buscador.listar(FiltrosDeAreas(solo_area_id=None, restringir_a_un_area=True), 10, None)

    assert [area.codigo for area in propia] == ["HOSP-02"]
    assert ninguna == []


async def test_busca_por_nombre_sin_tildes_ni_mayusculas(engine: AsyncEngine) -> None:
    await _escenario(engine)

    areas = await SqlAreaFinder(engine).listar(FiltrosDeAreas(texto="NANDU"), 10, None)

    assert [area.codigo for area in areas] == ["HOSP-01"]


@pytest.mark.parametrize("texto", ["1234", "00001234"])
async def test_busca_por_codigo_renipress_con_o_sin_ceros_a_la_izquierda(engine: AsyncEngine, texto: str) -> None:
    await _escenario(engine)

    areas = await SqlAreaFinder(engine).listar(FiltrosDeAreas(texto=texto), 10, None)

    assert [area.codigo for area in areas] == ["HOSP-01"]


async def test_el_cursor_continua_despues_de_la_posicion_dada(engine: AsyncEngine) -> None:
    await _escenario(engine)

    areas = await SqlAreaFinder(engine).listar(FiltrosDeAreas(), 10, PosicionPorNombre("Clínica Central", 11))

    assert [area.codigo for area in areas] == ["HOSP-01", "OTRANS"]


async def test_no_lista_areas_desactivadas(engine: AsyncEngine) -> None:
    await _escenario(engine)
    async with transaction(engine, ACTOR_DE_PRUEBA) as conexion:
        await conexion.execute(text("UPDATE catalogo.area SET activo = false WHERE id = 11"))

    areas = await SqlAreaFinder(engine).listar(FiltrosDeAreas(), 10, None)

    assert "HOSP-02" not in [area.codigo for area in areas]
