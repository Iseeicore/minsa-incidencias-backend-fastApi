from dataclasses import FrozenInstanceError

import pytest

from app.incidencias.domain.fila_historial import ItemDeHistorial


def test_el_item_de_historial_es_inmutable() -> None:
    item = ItemDeHistorial("titulo", "detalle", "hace 1 h", "2026-10-24T12:00:00.000Z")

    with pytest.raises(FrozenInstanceError):
        item.titulo = "otro"  # type: ignore[misc]
