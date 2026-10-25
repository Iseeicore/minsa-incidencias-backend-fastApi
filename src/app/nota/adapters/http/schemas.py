from datetime import datetime
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.nota.domain.constantes import CONTENIDO_MAX_LENGTH, TITULO_MAX_LENGTH

if TYPE_CHECKING:
    from app.nota.domain.nota import Nota


class CrearNotaRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    titulo: str = Field(max_length=TITULO_MAX_LENGTH)
    contenido: str = Field(max_length=CONTENIDO_MAX_LENGTH)


class NotaResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    codigo: str
    titulo: str
    contenido: str
    creada_en: datetime

    @classmethod
    def desde_dominio(cls, nota: Nota) -> Self:
        return cls(
            codigo=nota.codigo.valor, titulo=nota.titulo.valor, contenido=nota.contenido.valor, creada_en=nota.creada_en
        )
