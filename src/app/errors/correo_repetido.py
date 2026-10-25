from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class CorreoRepetido(DomainError):
    category = ErrorCategory.CONFLICT
    error_code = ErrorCode.CORREO_REPETIDO
