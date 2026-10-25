from dataclasses import FrozenInstanceError

import pytest

from tests.helpers.builders import una_sesion_vigente


def test_la_sesion_vigente_es_inmutable() -> None:
    with pytest.raises(FrozenInstanceError):
        una_sesion_vigente().debe_tocar = True  # type: ignore[misc]


def test_la_sesion_vigente_informa_si_debe_tocarse() -> None:
    assert una_sesion_vigente(debe_tocar=True).debe_tocar is True
    assert una_sesion_vigente().debe_tocar is False
