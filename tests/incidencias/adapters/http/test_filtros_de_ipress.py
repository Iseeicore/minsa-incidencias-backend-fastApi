import pytest

from app.errors.datos_invalidos import DatosInvalidos
from app.incidencias.adapters.http.filtros_de_ipress import consulta_de_ipress
from app.incidencias.domain.ipress import ConsultaDeIpress
from app.shared.cursor import PosicionPorNombre, encode_int_cursor


def test_sin_parametros_se_pide_la_primera_pagina_sin_texto() -> None:
    assert consulta_de_ipress(q=None, limite=50, cursor=None) == ConsultaDeIpress(limite=50)


def test_el_texto_vacio_equivale_a_no_buscar() -> None:
    assert consulta_de_ipress(q="", limite=10, cursor=None).texto is None


def test_el_texto_y_el_cursor_validos_pasan_a_la_consulta() -> None:
    posicion = PosicionPorNombre("Centro Uno", 4)

    consulta = consulta_de_ipress(q="centro", limite=5, cursor=encode_int_cursor(posicion))

    assert consulta == ConsultaDeIpress(limite=5, despues_de=posicion, texto="centro")


def test_un_cursor_alterado_responde_400_con_su_ruta() -> None:
    with pytest.raises(DatosInvalidos) as capturado:
        consulta_de_ipress(q=None, limite=50, cursor="###")

    assert capturado.value.details == [{"path": "cursor", "message": "El cursor no es válido."}]
