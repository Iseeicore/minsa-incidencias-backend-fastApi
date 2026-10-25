from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class DatabaseUnavailable(DomainError):
    category = ErrorCategory.UNAVAILABLE
    error_code = ErrorCode.DATABASE_UNAVAILABLE

    def __init__(self) -> None:
        super().__init__("El servicio no está disponible")
