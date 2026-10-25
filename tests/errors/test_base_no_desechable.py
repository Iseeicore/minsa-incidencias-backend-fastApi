from app.errors.base_no_desechable import BaseNoDesechable


def test_el_error_nombra_los_sufijos_que_aceptan_los_comandos() -> None:
    assert "_desechable, _dev, _local" in str(BaseNoDesechable())
    assert isinstance(BaseNoDesechable(), ValueError)
