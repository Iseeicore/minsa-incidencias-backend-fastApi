from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from app.enums.alcance_indicadores import AlcanceIndicadores
    from app.enums.categoria_filtro import CategoriaFiltro
    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.estado_api import EstadoApi
    from app.enums.estado_incidencia import EstadoIncidencia
    from app.enums.periodo_indicadores import PeriodoIndicadores
    from app.enums.tarjeta_codigo import TarjetaCodigo
    from app.enums.tipo_area import TipoArea
    from app.incidencias.domain.consultas import Visibilidad
    from app.incidencias.domain.cubos_de_evolucion import CuboDeEvolucion


@dataclass(frozen=True, slots=True)
class FilaResumen:
    generado_en: datetime
    recibidos: int
    recibidos_anterior: int
    pendientes: int
    en_gestion: int
    por_vencer: int
    vencidos: int
    resueltos: int
    resueltos_anterior: int
    sin_clasificar: int
    por_revisar: int
    sin_tomar: int
    corregidas_a_corrupcion: int
    corregidas_a_corrupcion_anterior: int
    segundos_promedio_de_resolucion: float | None


@dataclass(frozen=True, slots=True)
class FilaDistribucion:
    estado: EstadoIncidencia
    categoria: CategoriaIncidencia | None
    cantidad: int


@dataclass(frozen=True, slots=True)
class AreaDeAlcance:
    codigo: str
    nombre: str
    tipo: TipoArea


@dataclass(frozen=True, slots=True)
class AlcanceDeIndicadores:
    tipo: AlcanceIndicadores
    area: AreaDeAlcance | None


@dataclass(frozen=True, slots=True)
class ConsultaDeIndicadores:
    visible: Visibilidad
    alcance: AlcanceDeIndicadores


@dataclass(frozen=True, slots=True)
class TarjetaDeIndicador:
    codigo: TarjetaCodigo
    valor: int
    anterior: int | None


@dataclass(frozen=True, slots=True)
class CantidadPorCategoria:
    categoria: CategoriaFiltro
    cantidad: int


@dataclass(frozen=True, slots=True)
class CantidadPorEstado:
    estado: EstadoApi
    cantidad: int


@dataclass(frozen=True, slots=True)
class Indicadores:
    periodo: PeriodoIndicadores
    generado_en: str
    alcance: AlcanceDeIndicadores
    tarjetas: tuple[TarjetaDeIndicador, ...]
    por_categoria: tuple[CantidadPorCategoria, ...]
    por_estado: tuple[CantidadPorEstado, ...]
    evolucion: tuple[CuboDeEvolucion, ...]
    tiempo_promedio_horas: float | None


@dataclass(frozen=True, slots=True)
class ResumenDeIpress:
    total: int
    abiertos: int
    en_gestion: int
    resueltos: int
    archivados: int
    por_categoria: tuple[CantidadPorCategoria, ...]
