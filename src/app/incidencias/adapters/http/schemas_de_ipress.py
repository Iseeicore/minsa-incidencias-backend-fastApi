from typing import TYPE_CHECKING, Self

from app.enums.tipo_area import TipoArea
from app.shared.api_model import ApiModel
from app.shared.pagina_response import PaginaResponse

if TYPE_CHECKING:
    from app.incidencias.domain.ipress import IpressListada
    from app.shared.pagination import Pagina


class EstablecimientoDeIpressResponse(ApiModel):
    codigo_renipress: str
    nivel_atencion: str | None
    categoria: str | None


class IpressListadaResponse(ApiModel):
    id: int
    codigo: str
    nombre: str
    tipo_area: TipoArea
    establecimiento: EstablecimientoDeIpressResponse

    @classmethod
    def desde_dominio(cls, ipress: IpressListada) -> Self:
        return cls(
            id=ipress.id,
            codigo=ipress.codigo,
            nombre=ipress.nombre,
            tipo_area=TipoArea.ESTABLECIMIENTO,
            establecimiento=EstablecimientoDeIpressResponse(
                codigo_renipress=ipress.codigo_renipress,
                nivel_atencion=ipress.nivel_atencion,
                categoria=ipress.categoria,
            ),
        )


class PaginaDeIpressResponse(PaginaResponse[IpressListadaResponse]):
    @classmethod
    def desde_dominio(cls, pagina: Pagina[IpressListada]) -> Self:
        return cls(
            items=[IpressListadaResponse.desde_dominio(ipress) for ipress in pagina.items],
            siguiente=pagina.siguiente,
            hay_mas=pagina.hay_mas,
        )
