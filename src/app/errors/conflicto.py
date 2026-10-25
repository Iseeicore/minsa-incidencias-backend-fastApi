from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class Conflicto(DomainError):
    category = ErrorCategory.CONFLICT
    error_code = ErrorCode.CONFLICT

    def __init__(self, message: str | None = None, code: ErrorCode = ErrorCode.CONFLICT) -> None:
        self.error_code = code
        super().__init__(message)
