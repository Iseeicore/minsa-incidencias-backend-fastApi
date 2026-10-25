from typing import TYPE_CHECKING, Self

from app.enums.tipo_area import TipoArea
from app.shared.api_model import ApiModel
from app.shared.pagina_response import PaginaResponse

if TYPE_CHECKING:
    from app.catalogos.domain.area_listada import AreaListada
    from app.shared.pagination import Pagina


class EstablecimientoDeAreaResponse(ApiModel):
    codigo_renipress: str
    nivel_atencion: str | None
    categoria: str | None


class AreaListadaResponse(ApiModel):
    id: int
    codigo: str
    nombre: str
    tipo_area: TipoArea
    establecimiento: EstablecimientoDeAreaResponse | None

    @classmethod
    def desde_dominio(cls, area: AreaListada) -> Self:
        establecimiento = (
            EstablecimientoDeAreaResponse(
                codigo_renipress=area.establecimiento.codigo_renipress,
                nivel_atencion=area.establecimiento.nivel_atencion,
                categoria=area.establecimiento.categoria,
            )
            if area.establecimiento is not None
            else None
        )
        return cls(
            id=area.id,
            codigo=area.codigo,
            nombre=area.nombre,
            tipo_area=area.tipo_area,
            establecimiento=establecimiento,
        )


class PaginaDeAreasResponse(PaginaResponse[AreaListadaResponse]):
    @classmethod
    def desde_dominio(cls, pagina: Pagina[AreaListada]) -> Self:
        return cls(
            items=[AreaListadaResponse.desde_dominio(area) for area in pagina.items],
            siguiente=pagina.siguiente,
            hay_mas=pagina.hay_mas,
        )
