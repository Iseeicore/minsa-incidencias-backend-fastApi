from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.sin_sesion import SinSesion


def test_la_falta_de_sesion_es_un_error_de_autenticacion_con_el_mensaje_del_contrato() -> None:
    error = SinSesion()

    assert (error.category, error.error_code) == (ErrorCategory.UNAUTHENTICATED, ErrorCode.UNAUTHORIZED)
    assert error.message == "Debes iniciar sesión."
    assert error.details is None
