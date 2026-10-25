from typing import TYPE_CHECKING

from app.constants.textos.errores import DEFAULT_ERROR_MESSAGES

if TYPE_CHECKING:
    from app.enums.error_category import ErrorCategory
    from app.enums.error_code import ErrorCode


class DomainError(Exception):
    category: ErrorCategory
    error_code: ErrorCode
    headers: dict[str, str] | None = None

    def __init__(self, message: str | None = None, details: list[dict[str, str]] | None = None) -> None:
        text = message if message is not None else DEFAULT_ERROR_MESSAGES[self.error_code]
        super().__init__(text)
        self.message = text
        self.details = details
