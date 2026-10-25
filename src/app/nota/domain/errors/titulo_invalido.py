from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError
from app.nota.domain.constantes import TITULO_MAX_LENGTH


class TituloInvalido(DomainError):
    category = ErrorCategory.BUSINESS_RULE
    error_code = ErrorCode.NOTA_TITULO_INVALID

    def __init__(self) -> None:
        super().__init__("El título es obligatorio y tiene un máximo de caracteres", {"max": TITULO_MAX_LENGTH})
        self.max_length = TITULO_MAX_LENGTH
