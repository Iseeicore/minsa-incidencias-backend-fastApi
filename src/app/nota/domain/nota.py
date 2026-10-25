from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from app.nota.domain.contenido_nota import ContenidoNota
from app.nota.domain.errors.fecha_sin_zona_horaria import FechaSinZonaHoraria
from app.nota.domain.titulo_nota import TituloNota

if TYPE_CHECKING:
    from datetime import datetime

    from app.nota.domain.codigo_nota import CodigoNota


@dataclass(frozen=True, slots=True)
class Nota:
    codigo: CodigoNota
    titulo: TituloNota
    contenido: ContenidoNota
    creada_en: datetime

    @classmethod
    def crear(cls, codigo: CodigoNota, titulo: str, contenido: str, ahora: datetime) -> Self:
        if ahora.tzinfo is None:
            raise FechaSinZonaHoraria
        return cls(codigo=codigo, titulo=TituloNota(titulo), contenido=ContenidoNota(contenido), creada_en=ahora)
