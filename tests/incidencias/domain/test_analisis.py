from dataclasses import FrozenInstanceError

import pytest

from app.incidencias.domain.analisis import AreaMencionada, SenalDeAnalisis


def test_una_senal_lleva_frase_tipo_y_peso() -> None:
    senal = SenalDeAnalisis("me pidió plata", "FUERTE", 3)

    assert (senal.frase, senal.tipo, senal.peso) == ("me pidió plata", "FUERTE", 3)


def test_los_datos_del_analisis_no_se_modifican() -> None:
    area = AreaMencionada("OTRANS", "Oficina")

    with pytest.raises(FrozenInstanceError):
        area.codigo = "OTRO"  # type: ignore[misc]
