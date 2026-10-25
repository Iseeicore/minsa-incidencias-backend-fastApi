from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.constants.incidencias import CATEGORIA_API
from app.enums.categoria_api import CategoriaApi

if TYPE_CHECKING:
    from app.catalogos.domain.plazo_de_categoria import PlazoDeCategoria


class PlazoDeCategoriaResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    categoria: CategoriaApi
    plazo_dias_habiles: int
    archiva_por_vencimiento: bool

    @classmethod
    def desde_dominio(cls, plazo: PlazoDeCategoria) -> Self:
        return cls(
            categoria=CATEGORIA_API[plazo.categoria],
            plazo_dias_habiles=plazo.plazo_dias_habiles,
            archiva_por_vencimiento=plazo.archiva_por_vencimiento,
        )


class PlazosDeCategoriasResponse(BaseModel):
    items: list[PlazoDeCategoriaResponse]

    @classmethod
    def desde_dominio(cls, plazos: list[PlazoDeCategoria]) -> Self:
        return cls(items=[PlazoDeCategoriaResponse.desde_dominio(plazo) for plazo in plazos])
