from app.catalogos.application.listar_areas import ListarAreas
from app.catalogos.domain.area_listada import AreaListada, ConsultaAreas
from app.enums.tipo_area import TipoArea
from app.shared.cursor import PosicionPorNombre, decode_int_cursor
from tests.helpers.acceso_en_memoria import AreasEnMemoria
from tests.helpers.builders import un_area_de_sesion, una_sesion


def _area(identificador: int) -> AreaListada:
    return AreaListada(identificador, f"A-{identificador}", f"Area {identificador}", TipoArea.ESTABLECIMIENTO, None)


async def test_quien_ve_todas_las_areas_no_restringe_la_consulta() -> None:
    areas = AreasEnMemoria([_area(1)])

    pagina = await ListarAreas(areas).execute(
        una_sesion(roles=("ADMINISTRADOR",)), ConsultaAreas(limite=10, tipo=TipoArea.OTRANS, texto="hosp")
    )

    filtros, limite, _ = areas.consultas[0]
    assert (filtros.restringir_a_un_area, filtros.solo_area_id) == (False, None)
    assert (filtros.tipo, filtros.texto) == (TipoArea.OTRANS, "hosp")
    assert limite == 11
    assert [area.id for area in pagina.items] == [1]


async def test_quien_solo_ve_la_suya_queda_restringido_a_su_area() -> None:
    areas = AreasEnMemoria([_area(7)])
    sesion = una_sesion(roles=("ESTABLECIMIENTO",), area=un_area_de_sesion(id=7))

    await ListarAreas(areas).execute(sesion, ConsultaAreas(limite=10))

    filtros, _, _ = areas.consultas[0]
    assert (filtros.restringir_a_un_area, filtros.solo_area_id) == (True, 7)


async def test_quien_solo_ve_la_suya_pero_no_tiene_area_queda_sin_nada() -> None:
    areas = AreasEnMemoria([])

    await ListarAreas(areas).execute(una_sesion(roles=("OTRANS",)), ConsultaAreas(limite=10))

    filtros, _, _ = areas.consultas[0]
    assert (filtros.restringir_a_un_area, filtros.solo_area_id) == (True, None)


async def test_la_pagina_trae_el_cursor_numerico_del_ultimo_elemento() -> None:
    areas = AreasEnMemoria([_area(1), _area(2), _area(3)])

    pagina = await ListarAreas(areas).execute(
        una_sesion(roles=("ADMINISTRADOR",)), ConsultaAreas(limite=2, despues_de=PosicionPorNombre("Area 0", 0))
    )

    assert pagina.hay_mas is True
    assert decode_int_cursor(pagina.siguiente or "") == PosicionPorNombre("Area 2", 2)
    assert areas.consultas[0][2] == PosicionPorNombre("Area 0", 0)
