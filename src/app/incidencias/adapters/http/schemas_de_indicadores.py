from typing import TYPE_CHECKING, Self

from app.enums.alcance_indicadores import AlcanceIndicadores
from app.enums.categoria_filtro import CategoriaFiltro
from app.enums.estado_api import EstadoApi
from app.enums.periodo_indicadores import PeriodoIndicadores
from app.enums.tarjeta_codigo import TarjetaCodigo
from app.enums.tipo_area import TipoArea
from app.shared.api_model import ApiModel

if TYPE_CHECKING:
    from app.incidencias.domain.indicadores import CantidadPorCategoria, Indicadores, ResumenDeIpress


class AreaDeAlcanceResponse(ApiModel):
    codigo: str
    nombre: str
    tipo: TipoArea


class AlcanceResponse(ApiModel):
    tipo: AlcanceIndicadores
    area: AreaDeAlcanceResponse | None


class TarjetaResponse(ApiModel):
    codigo: TarjetaCodigo
    valor: int
    anterior: int | None


class CantidadPorCategoriaResponse(ApiModel):
    categoria: CategoriaFiltro
    cantidad: int

    @classmethod
    def desde_dominio(cls, fila: CantidadPorCategoria) -> Self:
        return cls(categoria=fila.categoria, cantidad=fila.cantidad)


class CantidadPorEstadoResponse(ApiModel):
    estado: EstadoApi
    cantidad: int


class CuboDeEvolucionResponse(ApiModel):
    desde: str
    recibidos: int
    resueltos: int


class IndicadoresResponse(ApiModel):
    periodo: PeriodoIndicadores
    generado_en: str
    alcance: AlcanceResponse
    tarjetas: list[TarjetaResponse]
    por_categoria: list[CantidadPorCategoriaResponse]
    por_estado: list[CantidadPorEstadoResponse]
    evolucion: list[CuboDeEvolucionResponse]
    tiempo_promedio_horas: float | None

    @classmethod
    def desde_dominio(cls, indicadores: Indicadores) -> Self:
        area = indicadores.alcance.area
        return cls(
            periodo=indicadores.periodo,
            generado_en=indicadores.generado_en,
            alcance=AlcanceResponse(
                tipo=indicadores.alcance.tipo,
                area=AreaDeAlcanceResponse(codigo=area.codigo, nombre=area.nombre, tipo=area.tipo)
                if area is not None
                else None,
            ),
            tarjetas=[
                TarjetaResponse(codigo=tarjeta.codigo, valor=tarjeta.valor, anterior=tarjeta.anterior)
                for tarjeta in indicadores.tarjetas
            ],
            por_categoria=[CantidadPorCategoriaResponse.desde_dominio(fila) for fila in indicadores.por_categoria],
            por_estado=[
                CantidadPorEstadoResponse(estado=fila.estado, cantidad=fila.cantidad) for fila in indicadores.por_estado
            ],
            evolucion=[
                CuboDeEvolucionResponse(desde=cubo.desde, recibidos=cubo.recibidos, resueltos=cubo.resueltos)
                for cubo in indicadores.evolucion
            ],
            tiempo_promedio_horas=indicadores.tiempo_promedio_horas,
        )


class ResumenDeIpressResponse(ApiModel):
    total: int
    abiertos: int
    en_gestion: int
    resueltos: int
    archivados: int
    por_categoria: list[CantidadPorCategoriaResponse]

    @classmethod
    def desde_dominio(cls, resumen: ResumenDeIpress) -> Self:
        return cls(
            total=resumen.total,
            abiertos=resumen.abiertos,
            en_gestion=resumen.en_gestion,
            resueltos=resumen.resueltos,
            archivados=resumen.archivados,
            por_categoria=[CantidadPorCategoriaResponse.desde_dominio(fila) for fila in resumen.por_categoria],
        )
