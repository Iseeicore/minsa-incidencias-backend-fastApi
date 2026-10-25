from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class DatosInvalidos(DomainError):
    category = ErrorCategory.VALIDATION
    error_code = ErrorCode.VALIDATION_FAILED
