from dataclasses import dataclass

from app.nota.domain.constantes import TITULO_MAX_LENGTH
from app.nota.domain.errors.titulo_invalido import TituloInvalido


@dataclass(frozen=True, slots=True)
class TituloNota:
    valor: str

    def __post_init__(self) -> None:
        limpio = self.valor.strip()
        if not limpio or len(limpio) > TITULO_MAX_LENGTH:
            raise TituloInvalido
        object.__setattr__(self, "valor", limpio)
