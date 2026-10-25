import pytest

from app.errors.base_no_desechable import BaseNoDesechable
from app.shared.base_desechable import asegurar_base_desechable


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:c@host:5432/minsa_desechable",
        "postgresql://u:c@host/pruebas_dev",
        "postgresql://u:c@host/mi_base_local",
        "postgresql+psycopg://u:c@host/ba%73e_desechable",
    ],
)
def test_una_base_con_sufijo_de_desechable_se_acepta(url: str) -> None:
    asegurar_base_desechable(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:c@host/minsa",
        "postgresql://u:c@host/desechable_produccion",
        "postgresql://u:c@host",
        "postgresql://u:c@host/",
    ],
)
def test_cualquier_otra_base_se_rechaza_con_los_sufijos_validos(url: str) -> None:
    with pytest.raises(BaseNoDesechable, match="_desechable, _dev, _local"):
        asegurar_base_desechable(url)
