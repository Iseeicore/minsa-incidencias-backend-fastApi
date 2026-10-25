from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class CodigoNotaInvalido(DomainError):
    category = ErrorCategory.VALIDATION
    error_code = ErrorCode.NOTA_CODIGO_INVALID

    def __init__(self, valor: str) -> None:
        super().__init__("El código de la nota no tiene el formato esperado", {"valor": valor})
        self.valor = valor
