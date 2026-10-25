from app.constants.textos.errores import SIN_SESION_MESSAGE
from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class SinSesion(DomainError):
    category = ErrorCategory.UNAUTHENTICATED
    error_code = ErrorCode.UNAUTHORIZED

    def __init__(self) -> None:
        super().__init__(SIN_SESION_MESSAGE)
