from dataclasses import FrozenInstanceError

import pytest

from tests.helpers.builders import un_usuario_interno


def test_el_usuario_interno_es_inmutable() -> None:
    with pytest.raises(FrozenInstanceError):
        un_usuario_interno().activo = False  # type: ignore[misc]


def test_el_usuario_interno_se_compara_por_valor() -> None:
    assert un_usuario_interno() == un_usuario_interno()
    assert un_usuario_interno() != un_usuario_interno(activo=False)
