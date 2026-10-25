from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.enums.categoria_filtro import CategoriaFiltro
    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.estado_api import EstadoApi
    from app.enums.estado_incidencia import EstadoIncidencia
    from app.enums.motivo_archivo import MotivoArchivo
    from app.incidencias.domain.cursores import PosicionDeListado, PosicionPorVencer


@dataclass(frozen=True, slots=True)
class FiltrosConsulta:
    estado: EstadoApi | None = None
    categoria: CategoriaFiltro | None = None
    texto: str | None = None
    establecimiento: str | None = None
    motivo_archivo: MotivoArchivo | None = None
    desde: str | None = None
    hasta: str | None = None
    por_vencer: bool = False


@dataclass(frozen=True, slots=True)
class ConsultaListado:
    limite: int
    filtros: FiltrosConsulta = field(default_factory=FiltrosConsulta)
    despues_de: PosicionDeListado | None = None
    despues_de_por_vencer: PosicionPorVencer | None = None


@dataclass(frozen=True, slots=True)
class FiltrosCasos:
    estado: EstadoIncidencia | None = None
    categoria: CategoriaIncidencia | None = None
    sin_categoria: bool = False
    texto: str | None = None
    establecimiento: str | None = None
    motivo_archivo: MotivoArchivo | None = None
    desde: str | None = None
    hasta: str | None = None
    aviso_horas: int | None = None


@dataclass(frozen=True, slots=True)
class VisibilidadOperativa:
    roles: tuple[str, ...]
    ver_sin_categoria: bool
    area_id: int | None


@dataclass(frozen=True, slots=True)
class VisibilidadDeDerivaciones:
    ver_sin_categoria: bool = True


@dataclass(frozen=True, slots=True)
class VisibilidadDeIpress:
    establecimiento_id: int
    ver_sin_categoria: bool = True


type Visibilidad = VisibilidadOperativa | VisibilidadDeDerivaciones | VisibilidadDeIpress
