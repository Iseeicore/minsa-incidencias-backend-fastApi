from dataclasses import dataclass
from typing import Self

from app.nota.domain.constantes import DIGITOS_CODIGO, PREFIJO_CODIGO
from app.nota.domain.errors.codigo_nota_invalido import CodigoNotaInvalido
from app.nota.domain.patrones import PATRON_CODIGO


@dataclass(frozen=True, slots=True)
class CodigoNota:
    valor: str

    def __post_init__(self) -> None:
        if not PATRON_CODIGO.fullmatch(self.valor):
            raise CodigoNotaInvalido(self.valor)

    @classmethod
    def desde_numero(cls, numero: int) -> Self:
        return cls(f"{PREFIJO_CODIGO}{numero:0{DIGITOS_CODIGO}d}")
