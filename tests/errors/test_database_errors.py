import pytest

from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.database_timeout import DatabaseTimeout
from app.errors.database_unavailable import DatabaseUnavailable


@pytest.mark.parametrize("error", [DatabaseUnavailable(), DatabaseTimeout()], ids=["no-disponible", "tiempo-agotado"])
def test_los_errores_de_la_base_son_internos_con_el_mensaje_por_defecto(
    error: DatabaseUnavailable | DatabaseTimeout,
) -> None:
    assert (error.category, error.error_code) == (ErrorCategory.INTERNAL, ErrorCode.INTERNAL_ERROR)
    assert error.message == "Ocurrió un error interno. Inténtalo más tarde."
    assert error.details is None
