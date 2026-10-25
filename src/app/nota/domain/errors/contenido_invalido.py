from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError
from app.nota.domain.constantes import CONTENIDO_MAX_LENGTH


class ContenidoInvalido(DomainError):
    category = ErrorCategory.BUSINESS_RULE
    error_code = ErrorCode.NOTA_CONTENIDO_INVALID

    def __init__(self) -> None:
        super().__init__("El contenido supera el máximo de caracteres", {"max": CONTENIDO_MAX_LENGTH})
        self.max_length = CONTENIDO_MAX_LENGTH
