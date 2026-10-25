from dataclasses import FrozenInstanceError, replace

import pytest

from tests.helpers.builders import un_usuario_gestionado


def test_el_usuario_gestionado_es_inmutable() -> None:
    with pytest.raises(FrozenInstanceError):
        un_usuario_gestionado().activo = False  # type: ignore[misc]


def test_un_cambio_produce_una_copia_distinta() -> None:
    usuario = un_usuario_gestionado()

    assert replace(usuario, activo=False) != usuario
