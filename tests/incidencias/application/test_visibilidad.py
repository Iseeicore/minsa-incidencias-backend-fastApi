from app.incidencias.application.visibilidad import VISIBILIDAD_DE_DERIVACIONES, visibilidad_de, visibilidad_o_de
from app.incidencias.domain.consultas import VisibilidadDeDerivaciones, VisibilidadDeIpress
from tests.helpers.builders import un_area_de_sesion, una_sesion


def test_el_administrador_ve_los_casos_sin_categoria_y_no_tiene_area() -> None:
    visible = visibilidad_de(una_sesion(roles=("ADMINISTRADOR",)))

    assert (visible.roles, visible.ver_sin_categoria, visible.area_id) == (("ADMINISTRADOR",), True, None)


def test_un_gestor_con_area_lleva_su_area_y_no_ve_casos_sin_categoria() -> None:
    visible = visibilidad_de(una_sesion(roles=("GESTOR",), area=un_area_de_sesion(id=7)))

    assert (visible.ver_sin_categoria, visible.area_id) == (False, 7)


def test_la_visibilidad_del_seguimiento_ve_los_casos_sin_categoria() -> None:
    assert VisibilidadDeDerivaciones(ver_sin_categoria=True) == VISIBILIDAD_DE_DERIVACIONES


def test_sin_visibilidad_explicita_se_usa_la_de_la_sesion() -> None:
    sesion = una_sesion(roles=("GESTOR",), area=un_area_de_sesion(id=7))

    assert visibilidad_o_de(sesion, None) == visibilidad_de(sesion)


def test_una_visibilidad_explicita_manda_sobre_la_de_la_sesion() -> None:
    sesion = una_sesion(roles=("GESTOR",), area=un_area_de_sesion(id=7))
    de_ipress = VisibilidadDeIpress(establecimiento_id=3)

    assert visibilidad_o_de(sesion, de_ipress) is de_ipress
