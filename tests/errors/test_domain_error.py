from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class ErrorDePrueba(DomainError):
    category = ErrorCategory.NOT_FOUND
    error_code = ErrorCode.NOT_FOUND


def test_un_error_de_dominio_declara_su_categoria_y_su_codigo() -> None:
    error = ErrorDePrueba("no existe", details=[{"path": "recurso", "message": "x"}])

    assert error.category is ErrorCategory.NOT_FOUND
    assert error.error_code is ErrorCode.NOT_FOUND
    assert error.message == "no existe"
    assert error.details == [{"path": "recurso", "message": "x"}]


def test_los_detalles_son_opcionales() -> None:
    assert ErrorDePrueba("no existe").details is None


def test_sin_mensaje_usa_el_texto_por_defecto_del_codigo() -> None:
    assert ErrorDePrueba().message == "El recurso solicitado no existe."
