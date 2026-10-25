from datetime import UTC, datetime

import pytest

from app.enums.categoria_api import CategoriaApi
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.situacion_derivacion import SituacionDerivacion
from app.errors.datos_invalidos import DatosInvalidos
from app.incidencias.adapters.http.filtros_de_derivacion import (
    consulta_de_derivaciones,
    filtros_de_conteos_de_derivacion,
)
from app.incidencias.domain.cursores import PosicionDeDerivacion, codificar_cursor_de_derivacion
from app.incidencias.domain.derivaciones import ConsultaDeDerivaciones, FiltrosDeDerivaciones

INSTANTE = datetime(2026, 10, 24, 12, 0, 0, 123_000, tzinfo=UTC)
MENSAJE_FECHA = "La fecha debe ser un día real con el formato AAAA-MM-DD."


def _consulta(**cambios: object) -> ConsultaDeDerivaciones:
    parametros: dict[str, object] = {
        "situacion": None,
        "texto": None,
        "establecimiento": None,
        "categoria": None,
        "desde": None,
        "hasta": None,
        "limite": 10,
        "cursor": None,
    }
    return consulta_de_derivaciones(**{**parametros, **cambios})  # type: ignore[arg-type]


def _errores(**cambios: object) -> list[dict[str, str]]:
    with pytest.raises(DatosInvalidos) as capturado:
        _consulta(**cambios)
    assert capturado.value.details is not None
    return capturado.value.details


def test_sin_parametros_no_se_filtra_y_se_pide_la_primera_pagina() -> None:
    consulta = _consulta()

    assert consulta == ConsultaDeDerivaciones(limite=10, filtros=FiltrosDeDerivaciones(), despues_de=None)


def test_los_filtros_validos_pasan_normalizados_y_la_categoria_se_traduce_al_dominio() -> None:
    consulta = _consulta(
        situacion=SituacionDerivacion.EN_GESTION,
        texto="000001",
        establecimiento="00001234",
        categoria=CategoriaApi.DENUNCIA_CORRUPCION,
        desde="2026-01-01",
        hasta="2026-01-31",
    )

    assert consulta.filtros == FiltrosDeDerivaciones(
        situacion=SituacionDerivacion.EN_GESTION,
        texto="000001",
        establecimiento="1234",
        categoria=CategoriaIncidencia.DENUNCIA_CORRUPCION,
        desde="2026-01-01",
        hasta="2026-01-31",
    )


@pytest.mark.parametrize(
    ("cambios", "ruta", "mensaje"),
    [
        ({"desde": "2026-02-30"}, "desde", MENSAJE_FECHA),
        ({"hasta": "ayer"}, "hasta", MENSAJE_FECHA),
        ({"establecimiento": "abc"}, "establecimiento", "El código del establecimiento no es válido."),
        ({"desde": "2026-03-10", "hasta": "2026-03-09"}, "desde", "La fecha «desde» no puede ser posterior a «hasta»."),
        ({"desde": "2025-01-01", "hasta": "2026-03-09"}, "hasta", "El rango no puede abarcar más de 366 días."),
        ({"cursor": "###"}, "cursor", "El cursor no es válido."),
    ],
)
def test_un_filtro_invalido_responde_con_la_ruta_y_el_mensaje_del_contrato(
    cambios: dict[str, object], ruta: str, mensaje: str
) -> None:
    assert _errores(**cambios) == [{"path": ruta, "message": mensaje}]


def test_el_cursor_de_derivaciones_se_decodifica() -> None:
    posicion = PosicionDeDerivacion(INSTANTE, "4821")

    consulta = _consulta(cursor=codificar_cursor_de_derivacion(posicion))

    assert consulta.despues_de == posicion


def test_un_cursor_de_otro_listado_se_rechaza() -> None:
    assert [error["path"] for error in _errores(cursor="eyJhIjoxfQ")] == ["cursor"]


def test_los_conteos_aceptan_los_mismos_filtros_incluida_la_situacion() -> None:
    filtros = filtros_de_conteos_de_derivacion(
        situacion=SituacionDerivacion.PENDIENTE,
        texto=None,
        establecimiento="0007",
        categoria=CategoriaApi.QUEJA,
        desde=None,
        hasta=None,
    )

    assert filtros == FiltrosDeDerivaciones(
        situacion=SituacionDerivacion.PENDIENTE, establecimiento="7", categoria=CategoriaIncidencia.QUEJA
    )


def test_los_conteos_rechazan_un_filtro_invalido() -> None:
    with pytest.raises(DatosInvalidos) as capturado:
        filtros_de_conteos_de_derivacion(
            situacion=None, texto=None, establecimiento="x", categoria=None, desde=None, hasta=None
        )

    assert capturado.value.details == [
        {"path": "establecimiento", "message": "El código del establecimiento no es válido."}
    ]
