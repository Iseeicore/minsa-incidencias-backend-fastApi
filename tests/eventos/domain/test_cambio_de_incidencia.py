import pytest

from app.enums.rol_codigo import RolCodigo
from app.eventos.domain.cambio_de_incidencia import (
    AlcanceDeEventos,
    CambioDeIncidencia,
    alcance_de_eventos,
    recibe_cambio,
)
from tests.helpers.eventos_en_memoria import CATEGORIAS, CORRUPCION, QUEJA

AREA = 5
OTRA_AREA = 6


def _alcance(area_id: int | None, *categorias: int, sin_categoria: bool = False) -> AlcanceDeEventos:
    return AlcanceDeEventos(
        ve_todo=False, ver_sin_categoria=sin_categoria, area_id=area_id, categorias=frozenset(categorias)
    )


@pytest.mark.parametrize("rol", [RolCodigo.ADMINISTRADOR, RolCodigo.OTRANS])
def test_administrador_y_otrans_ven_todos_los_cambios(rol: RolCodigo) -> None:
    alcance = alcance_de_eventos((rol,), None, CATEGORIAS)

    assert alcance.ve_todo is True
    assert recibe_cambio(alcance, CambioDeIncidencia(OTRA_AREA, OTRA_AREA, CORRUPCION, CORRUPCION)) is True


@pytest.mark.parametrize("rol", [RolCodigo.GESTOR, RolCodigo.ESTABLECIMIENTO])
def test_gestor_y_establecimiento_ven_solo_su_area_y_las_categorias_de_su_rol(rol: RolCodigo) -> None:
    alcance = alcance_de_eventos((rol,), AREA, CATEGORIAS)

    assert (alcance.ve_todo, alcance.area_id, alcance.categorias) == (False, AREA, frozenset({QUEJA}))
    assert recibe_cambio(alcance, CambioDeIncidencia(AREA, AREA, QUEJA, QUEJA)) is True
    assert recibe_cambio(alcance, CambioDeIncidencia(OTRA_AREA, OTRA_AREA, QUEJA, QUEJA)) is False
    assert recibe_cambio(alcance, CambioDeIncidencia(AREA, AREA, CORRUPCION, CORRUPCION)) is False


def test_un_roles_se_suman_y_un_rol_sin_categorias_no_aporta() -> None:
    alcance = alcance_de_eventos((RolCodigo.GESTOR, RolCodigo.OTRANS, "DESCONOCIDO"), AREA, CATEGORIAS)

    assert alcance.categorias == frozenset({QUEJA, CORRUPCION})


def test_sin_area_solo_recibe_quien_lo_ve_todo() -> None:
    sin_area = alcance_de_eventos((RolCodigo.GESTOR,), None, CATEGORIAS)

    assert recibe_cambio(sin_area, CambioDeIncidencia(AREA, AREA, QUEJA, QUEJA)) is False


def test_basta_que_el_area_de_antes_o_la_de_despues_sea_la_suya() -> None:
    alcance = _alcance(AREA, QUEJA)

    assert recibe_cambio(alcance, CambioDeIncidencia(AREA, OTRA_AREA, QUEJA, QUEJA)) is True
    assert recibe_cambio(alcance, CambioDeIncidencia(OTRA_AREA, AREA, QUEJA, QUEJA)) is True


def test_basta_que_la_categoria_de_antes_o_la_de_despues_sea_visible() -> None:
    alcance = _alcance(AREA, QUEJA)

    assert recibe_cambio(alcance, CambioDeIncidencia(AREA, AREA, CORRUPCION, QUEJA)) is True
    assert recibe_cambio(alcance, CambioDeIncidencia(AREA, AREA, QUEJA, CORRUPCION)) is True


@pytest.mark.parametrize(("ve_sin_categoria", "esperado"), [(True, True), (False, False)])
def test_un_caso_sin_categoria_solo_llega_a_quien_puede_verlo(*, ve_sin_categoria: bool, esperado: bool) -> None:
    alcance = _alcance(AREA, QUEJA, sin_categoria=ve_sin_categoria)

    assert recibe_cambio(alcance, CambioDeIncidencia(AREA, AREA, None, None)) is esperado
