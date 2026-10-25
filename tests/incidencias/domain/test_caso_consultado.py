from dataclasses import FrozenInstanceError

import pytest

from app.incidencias.domain.caso_consultado import ConteoPorVencer
from tests.helpers.builders import un_caso_consultado


def test_el_caso_consultado_es_inmutable() -> None:
    with pytest.raises(FrozenInstanceError):
        un_caso_consultado().codigo = "otro"  # type: ignore[misc]


def test_un_cambio_en_el_builder_se_refleja_en_el_caso() -> None:
    assert un_caso_consultado(codigo="MINSA-2026-000009").codigo == "MINSA-2026-000009"


def test_el_conteo_por_vencer_guarda_el_total_y_los_vencidos() -> None:
    assert (ConteoPorVencer(5, 2).total, ConteoPorVencer(5, 2).vencidos) == (5, 2)
