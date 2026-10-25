from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.domain_error import DomainError


class NotaNoEncontrada(DomainError):
    category = ErrorCategory.NOT_FOUND
    error_code = ErrorCode.NOTA_NOT_FOUND

    def __init__(self, codigo: str) -> None:
        super().__init__("La nota no existe", {"codigo": codigo})
        self.codigo = codigo
