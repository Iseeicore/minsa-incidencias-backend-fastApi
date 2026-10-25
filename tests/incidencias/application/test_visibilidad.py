from app.incidencias.application.visibilidad import visibilidad_de
from tests.helpers.builders import un_area_de_sesion, una_sesion


def test_el_administrador_ve_los_casos_sin_categoria_y_no_tiene_area() -> None:
    visible = visibilidad_de(una_sesion(roles=("ADMINISTRADOR",)))

    assert (visible.roles, visible.ver_sin_categoria, visible.area_id) == (("ADMINISTRADOR",), True, None)


def test_un_gestor_con_area_lleva_su_area_y_no_ve_casos_sin_categoria() -> None:
    visible = visibilidad_de(una_sesion(roles=("GESTOR",), area=un_area_de_sesion(id=7)))

    assert (visible.ver_sin_categoria, visible.area_id) == (False, 7)
