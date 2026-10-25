from dataclasses import dataclass

from app.nota.domain.constantes import CONTENIDO_MAX_LENGTH
from app.nota.domain.errors.contenido_invalido import ContenidoInvalido


@dataclass(frozen=True, slots=True)
class ContenidoNota:
    valor: str

    def __post_init__(self) -> None:
        if len(self.valor) > CONTENIDO_MAX_LENGTH:
            raise ContenidoInvalido
