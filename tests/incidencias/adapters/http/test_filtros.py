from datetime import UTC, datetime

import pytest

from app.enums.categoria_filtro import CategoriaFiltro
from app.enums.estado_api import EstadoApi
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.plazo_filtro import PlazoFiltro
from app.errors.datos_invalidos import DatosInvalidos
from app.incidencias.adapters.http.filtros import armar_filtros, consulta_de_listado, filtros_de_conteos
from app.incidencias.domain.cursores import (
    PosicionDeListado,
    PosicionPorVencer,
    codificar_cursor,
    codificar_cursor_por_vencer,
)

ID = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"
INSTANTE = datetime(2026, 10, 24, 12, 0, 0, 123_000, tzinfo=UTC)


def _listado(**cambios: object) -> object:
    parametros: dict[str, object] = {
        "estado": None,
        "motivo_archivo": None,
        "categoria": None,
        "texto": None,
        "establecimiento": None,
        "desde": None,
        "hasta": None,
        "plazo": None,
        "limite": 20,
        "cursor": None,
    }
    return consulta_de_listado(**{**parametros, **cambios})


def _errores(**cambios: object) -> list[dict[str, str]]:
    with pytest.raises(DatosInvalidos) as capturado:
        _listado(**cambios)
    assert capturado.value.details is not None
    return capturado.value.details


def test_sin_parametros_no_se_filtra_y_se_pide_la_pagina_por_defecto() -> None:
    consulta = _listado()

    assert (consulta.limite, consulta.filtros.estado, consulta.despues_de) == (20, None, None)  # type: ignore[attr-defined]


def test_los_filtros_validos_pasan_normalizados() -> None:
    consulta = _listado(
        estado=EstadoApi.RESUELTO,
        motivo_archivo=MotivoArchivo.NO_CORRESPONDE,
        categoria=CategoriaFiltro.SIN_CATEGORIA,
        texto="goteras",
        establecimiento="00001234",
        desde="2026-01-01",
        hasta="2026-01-31",
    )

    filtros = consulta.filtros  # type: ignore[attr-defined]
    assert (filtros.establecimiento, filtros.desde, filtros.hasta, filtros.texto) == (
        "1234",
        "2026-01-01",
        "2026-01-31",
        "goteras",
    )


@pytest.mark.parametrize(
    ("cambios", "ruta", "mensaje"),
    [
        ({"desde": "2026-02-30"}, "desde", "La fecha debe ser un día real con el formato AAAA-MM-DD."),
        ({"hasta": "ayer"}, "hasta", "La fecha debe ser un día real con el formato AAAA-MM-DD."),
        ({"establecimiento": "abc"}, "establecimiento", "El código del establecimiento no es válido."),
        ({"establecimiento": "123456789"}, "establecimiento", "El código del establecimiento no es válido."),
        ({"desde": "2026-03-10", "hasta": "2026-03-09"}, "desde", "La fecha «desde» no puede ser posterior a «hasta»."),
        ({"desde": "2025-01-01", "hasta": "2026-03-09"}, "hasta", "El rango no puede abarcar más de 366 días."),
        (
            {"plazo": PlazoFiltro.POR_VENCER, "estado": EstadoApi.RESUELTO},
            "plazo",
            "El plazo solo se aplica a los casos abiertos: no se combina con los estados «resuelto» y «archivado» ni con «motivoArchivo».",
        ),
        (
            {"plazo": PlazoFiltro.POR_VENCER, "motivo_archivo": MotivoArchivo.NO_CORRESPONDE},
            "plazo",
            "El plazo solo se aplica a los casos abiertos: no se combina con los estados «resuelto» y «archivado» ni con «motivoArchivo».",
        ),
        ({"cursor": "###"}, "cursor", "El cursor no es válido."),
    ],
)
def test_un_filtro_invalido_responde_con_la_ruta_y_el_mensaje_del_contrato(
    cambios: dict[str, object], ruta: str, mensaje: str
) -> None:
    assert _errores(**cambios) == [{"path": ruta, "message": mensaje}]


def test_el_rango_de_un_solo_dia_y_el_de_366_dias_son_validos() -> None:
    assert _listado(desde="2026-03-10", hasta="2026-03-10")
    assert _listado(desde="2024-01-01", hasta="2024-12-31")


def test_el_plazo_se_combina_con_los_estados_abiertos() -> None:
    consulta = _listado(plazo=PlazoFiltro.POR_VENCER, estado=EstadoApi.DERIVADO)

    assert consulta.filtros.por_vencer is True  # type: ignore[attr-defined]


def test_se_acumulan_todos_los_errores() -> None:
    errores = _errores(desde="no", hasta="tampoco", establecimiento="x", cursor="###")

    assert [error["path"] for error in errores] == ["desde", "hasta", "establecimiento", "cursor"]


def test_el_cursor_del_listado_se_decodifica_cuando_no_hay_plazo() -> None:
    posicion = PosicionDeListado(INSTANTE, ID)

    consulta = _listado(cursor=codificar_cursor(posicion))

    assert (consulta.despues_de, consulta.despues_de_por_vencer) == (posicion, None)  # type: ignore[attr-defined]


def test_el_cursor_por_vencer_se_decodifica_cuando_hay_plazo() -> None:
    posicion = PosicionPorVencer(INSTANTE, ID)

    consulta = _listado(plazo=PlazoFiltro.POR_VENCER, cursor=codificar_cursor_por_vencer(posicion))

    assert (consulta.despues_de, consulta.despues_de_por_vencer) == (None, posicion)  # type: ignore[attr-defined]


def test_un_cursor_de_un_tipo_no_sirve_con_el_filtro_del_otro() -> None:
    assert _errores(cursor=codificar_cursor(PosicionDeListado(INSTANTE, ID)), plazo=PlazoFiltro.POR_VENCER) == [
        {"path": "cursor", "message": "El cursor no es válido."}
    ]
    assert _errores(cursor=codificar_cursor_por_vencer(PosicionPorVencer(INSTANTE, ID))) == [
        {"path": "cursor", "message": "El cursor no es válido."}
    ]


def test_los_conteos_validan_los_mismos_filtros_pero_no_paginan() -> None:
    filtros = filtros_de_conteos(
        estado=EstadoApi.CLASIFICADO,
        motivo_archivo=None,
        categoria=None,
        texto=None,
        establecimiento="0012",
        desde=None,
        hasta=None,
        plazo=None,
    )

    assert (filtros.estado, filtros.establecimiento) == (EstadoApi.CLASIFICADO, "12")
    with pytest.raises(DatosInvalidos):
        filtros_de_conteos(
            estado=None,
            motivo_archivo=None,
            categoria=None,
            texto=None,
            establecimiento="xx",
            desde=None,
            hasta=None,
            plazo=None,
        )


def test_armar_filtros_acumula_los_errores_en_la_lista_recibida() -> None:
    errores: list[dict[str, str]] = []

    armar_filtros(None, None, None, "  ", "xx", None, None, None, errores)

    assert [error["path"] for error in errores] == ["establecimiento"]
