from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class EvidenciaNoDisponible(DomainError):
    category = ErrorCategory.NOT_FOUND
    error_code = ErrorCode.EVIDENCIA_NO_DISPONIBLE
