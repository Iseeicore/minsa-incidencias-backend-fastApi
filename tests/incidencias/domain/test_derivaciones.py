from dataclasses import FrozenInstanceError

import pytest

from app.incidencias.domain.derivaciones import ConsultaDeDerivaciones, FiltrosDeDerivaciones


def test_sin_filtros_ninguno_esta_activo() -> None:
    filtros = FiltrosDeDerivaciones()

    assert (filtros.situacion, filtros.texto, filtros.establecimiento) == (None, None, None)
    assert (filtros.categoria, filtros.desde, filtros.hasta) == (None, None, None)


def test_la_consulta_sin_filtros_ni_cursor_arranca_en_la_primera_pagina() -> None:
    consulta = ConsultaDeDerivaciones(limite=10)

    assert consulta.filtros == FiltrosDeDerivaciones()
    assert consulta.despues_de is None


def test_los_filtros_no_se_modifican() -> None:
    filtros = FiltrosDeDerivaciones(texto="000001")

    with pytest.raises(FrozenInstanceError):
        filtros.texto = "otro"  # type: ignore[misc]
