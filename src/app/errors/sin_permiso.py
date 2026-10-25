from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class SinPermiso(DomainError):
    category = ErrorCategory.FORBIDDEN
    error_code = ErrorCode.FORBIDDEN
