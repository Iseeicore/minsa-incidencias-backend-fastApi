from typing import TYPE_CHECKING, Self

from app.enums.categoria_api import CategoriaApi
from app.enums.estado_api import EstadoApi
from app.enums.motivo_archivo import MotivoArchivo
from app.incidencias.adapters.http.schemas import AreaDeCasoResponse, CasoDetalleResponse
from app.shared.api_model import ApiModel
from app.shared.pagina_response import PaginaResponse

if TYPE_CHECKING:
    from app.incidencias.domain.derivaciones import (
        ConteosDeDerivaciones,
        DerivacionDetalle,
        DerivacionResumen,
    )
    from app.shared.pagination import Pagina


class DestinoDeDerivacionResponse(ApiModel):
    codigo: str
    nombre: str
    codigo_renipress: str | None


class DerivacionResumenResponse(ApiModel):
    id: str
    codigo_caso: str
    fecha_derivacion: str
    origen: AreaDeCasoResponse
    destino: DestinoDeDerivacionResponse
    derivado_por: str
    descripcion: str | None
    categoria: CategoriaApi | None
    estado: EstadoApi
    motivo_archivo: MotivoArchivo | None

    @classmethod
    def desde_dominio(cls, derivacion: DerivacionResumen) -> Self:
        return cls(
            id=derivacion.id,
            codigo_caso=derivacion.codigo_caso,
            fecha_derivacion=derivacion.fecha_derivacion,
            origen=AreaDeCasoResponse(codigo=derivacion.origen.codigo, nombre=derivacion.origen.nombre),
            destino=DestinoDeDerivacionResponse(
                codigo=derivacion.destino.codigo,
                nombre=derivacion.destino.nombre,
                codigo_renipress=derivacion.destino.codigo_renipress,
            ),
            derivado_por=derivacion.derivado_por,
            descripcion=derivacion.descripcion,
            categoria=derivacion.categoria,
            estado=derivacion.estado,
            motivo_archivo=derivacion.motivo_archivo,
        )


class PaginaDeDerivacionesResponse(PaginaResponse[DerivacionResumenResponse]):
    @classmethod
    def desde_dominio(cls, pagina: Pagina[DerivacionResumen]) -> Self:
        return cls(
            items=[DerivacionResumenResponse.desde_dominio(derivacion) for derivacion in pagina.items],
            siguiente=pagina.siguiente,
            hay_mas=pagina.hay_mas,
        )


class ConteosDeDerivacionesResponse(ApiModel):
    todos: int
    pendientes: int
    en_gestion: int
    resueltos: int
    archivados: int

    @classmethod
    def desde_dominio(cls, conteos: ConteosDeDerivaciones) -> Self:
        return cls(
            todos=conteos.todos,
            pendientes=conteos.pendientes,
            en_gestion=conteos.en_gestion,
            resueltos=conteos.resueltos,
            archivados=conteos.archivados,
        )


class DerivacionDetalleResponse(ApiModel):
    derivacion: DerivacionResumenResponse
    caso: CasoDetalleResponse

    @classmethod
    def desde_dominio(cls, detalle: DerivacionDetalle) -> Self:
        return cls(
            derivacion=DerivacionResumenResponse.desde_dominio(detalle.derivacion),
            caso=CasoDetalleResponse.desde_dominio(detalle.caso),
        )
