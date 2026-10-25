from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class FechaSinZonaHoraria(DomainError):
    category = ErrorCategory.INTERNAL
    error_code = ErrorCode.INTERNAL_ERROR

    def __init__(self) -> None:
        super().__init__("La fecha de creación necesita zona horaria")
