from dataclasses import FrozenInstanceError

import pytest

from tests.helpers.builders import una_seguridad


def test_por_defecto_no_hay_origenes_permitidos_ni_proxy_confiable() -> None:
    seguridad = una_seguridad()

    assert seguridad.allowed_origins == ()
    assert seguridad.trust_proxy is False


def test_la_configuracion_es_inmutable() -> None:
    with pytest.raises(FrozenInstanceError):
        una_seguridad().trust_proxy = True  # type: ignore[misc]
