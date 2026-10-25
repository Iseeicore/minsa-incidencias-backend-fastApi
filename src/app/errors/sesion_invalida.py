from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class SesionInvalida(DomainError):
    category = ErrorCategory.UNAUTHENTICATED
    error_code = ErrorCode.INVALID_SESSION
