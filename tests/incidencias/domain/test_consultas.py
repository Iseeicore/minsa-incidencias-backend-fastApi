from app.incidencias.domain.consultas import ConsultaListado, FiltrosCasos, FiltrosConsulta, VisibilidadOperativa


def test_sin_indicar_nada_no_se_filtra_ni_se_pagina() -> None:
    assert FiltrosConsulta() == FiltrosConsulta(None, None, None, None, None, None, None, por_vencer=False)
    assert FiltrosCasos().sin_categoria is False
    consulta = ConsultaListado(limite=20)
    assert (consulta.filtros, consulta.despues_de, consulta.despues_de_por_vencer) == (FiltrosConsulta(), None, None)


def test_la_visibilidad_lleva_los_roles_el_permiso_de_sin_categoria_y_el_area() -> None:
    visible = VisibilidadOperativa(("GESTOR",), ver_sin_categoria=False, area_id=3)

    assert (visible.roles, visible.ver_sin_categoria, visible.area_id) == (("GESTOR",), False, 3)
