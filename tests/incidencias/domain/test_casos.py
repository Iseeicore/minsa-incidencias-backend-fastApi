from dataclasses import FrozenInstanceError

import pytest

from app.incidencias.domain.casos import AreaDeCaso, ConteoAcotado


def test_los_datos_de_un_caso_son_inmutables() -> None:
    with pytest.raises(FrozenInstanceError):
        AreaDeCaso("A", "Area").codigo = "B"  # type: ignore[misc]


def test_un_conteo_acotado_dice_si_hay_mas() -> None:
    assert ConteoAcotado(1000, con_mas=True).con_mas is True
