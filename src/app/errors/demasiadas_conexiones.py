from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class DemasiadasConexiones(DomainError):
    category = ErrorCategory.RATE_LIMITED
    error_code = ErrorCode.DEMASIADAS_CONEXIONES
