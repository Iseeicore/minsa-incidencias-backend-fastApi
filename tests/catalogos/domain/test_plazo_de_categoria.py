import dataclasses

import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia
from tests.helpers.builders import un_plazo


def test_dos_plazos_con_los_mismos_datos_son_iguales() -> None:
    assert un_plazo() == un_plazo()


def test_un_plazo_es_inmutable() -> None:
    plazo = un_plazo()

    with pytest.raises(dataclasses.FrozenInstanceError):
        plazo.plazo_dias_habiles = 1  # type: ignore[misc]


def test_un_plazo_conoce_su_categoria_y_si_archiva_por_vencimiento() -> None:
    plazo = un_plazo(CategoriaIncidencia.DENUNCIA_CORRUPCION, 3, archiva_por_vencimiento=False)

    assert plazo.categoria is CategoriaIncidencia.DENUNCIA_CORRUPCION
    assert plazo.plazo_dias_habiles == 3
    assert plazo.archiva_por_vencimiento is False
