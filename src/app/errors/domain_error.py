from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.enums.error_category import ErrorCategory
    from app.enums.error_code import ErrorCode


class DomainError(Exception):
    category: ErrorCategory
    error_code: ErrorCode

    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
