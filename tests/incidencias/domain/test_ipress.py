from app.incidencias.domain.ipress import ConsultaDeIpress, IpressConsultada, IpressListada


def test_la_consulta_sin_texto_ni_cursor_arranca_en_la_primera_pagina() -> None:
    consulta = ConsultaDeIpress(limite=50)

    assert (consulta.texto, consulta.despues_de) == (None, None)


def test_una_ipress_consultada_lleva_su_establecimiento_codigo_y_nombre() -> None:
    ipress = IpressConsultada(establecimiento_id=7, codigo="EESS-0001", nombre="Centro de Salud")

    assert (ipress.establecimiento_id, ipress.codigo, ipress.nombre) == (7, "EESS-0001", "Centro de Salud")


def test_una_ipress_listada_admite_nivel_y_categoria_nulos() -> None:
    ipress = IpressListada(1, "EESS-0001", "Centro de Salud", "1234", None, None)

    assert (ipress.codigo_renipress, ipress.nivel_atencion, ipress.categoria) == ("1234", None, None)
