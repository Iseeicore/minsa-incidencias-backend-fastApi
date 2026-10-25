import pytest

from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.database_timeout import DatabaseTimeout
from app.errors.database_unavailable import DatabaseUnavailable


@pytest.mark.parametrize(
    ("error", "categoria", "codigo", "mensaje"),
    [
        (
            DatabaseUnavailable(),
            ErrorCategory.UNAVAILABLE,
            ErrorCode.DATABASE_UNAVAILABLE,
            "El servicio no está disponible",
        ),
        (
            DatabaseTimeout(),
            ErrorCategory.TIMEOUT,
            ErrorCode.DATABASE_TIMEOUT,
            "El servicio tardó demasiado en responder",
        ),
    ],
    ids=["no-disponible", "tiempo-agotado"],
)
def test_los_errores_de_la_base_declaran_categoria_codigo_y_mensaje(
    error: DatabaseUnavailable | DatabaseTimeout, categoria: ErrorCategory, codigo: ErrorCode, mensaje: str
) -> None:
    assert (error.category, error.error_code, error.message) == (categoria, codigo, mensaje)
    assert error.details is None
