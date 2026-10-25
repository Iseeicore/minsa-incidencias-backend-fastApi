from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class DatabaseTimeout(DomainError):
    category = ErrorCategory.INTERNAL
    error_code = ErrorCode.INTERNAL_ERROR
