from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class DatabaseTimeout(DomainError):
    category = ErrorCategory.TIMEOUT
    error_code = ErrorCode.DATABASE_TIMEOUT

    def __init__(self) -> None:
        super().__init__("El servicio tardó demasiado en responder")
