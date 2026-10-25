from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class NoProcesable(DomainError):
    category = ErrorCategory.BUSINESS_RULE
    error_code = ErrorCode.UNPROCESSABLE
