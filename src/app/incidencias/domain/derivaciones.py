from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from app.enums.categoria_api import CategoriaApi
    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.estado_api import EstadoApi
    from app.enums.estado_incidencia import EstadoIncidencia
    from app.enums.motivo_archivo import MotivoArchivo
    from app.enums.situacion_derivacion import SituacionDerivacion
    from app.incidencias.domain.casos import AreaDeCaso, CasoDetalle
    from app.incidencias.domain.cursores import PosicionDeDerivacion


@dataclass(frozen=True, slots=True)
class FiltrosDeDerivaciones:
    situacion: SituacionDerivacion | None = None
    texto: str | None = None
    establecimiento: str | None = None
    categoria: CategoriaIncidencia | None = None
    desde: str | None = None
    hasta: str | None = None


@dataclass(frozen=True, slots=True)
class ConsultaDeDerivaciones:
    limite: int
    filtros: FiltrosDeDerivaciones = field(default_factory=FiltrosDeDerivaciones)
    despues_de: PosicionDeDerivacion | None = None


@dataclass(frozen=True, slots=True)
class DerivacionConsultada:
    id: str
    codigo_caso: str
    fecha_derivacion: datetime
    origen_codigo: str
    origen_nombre: str
    destino_codigo: str
    destino_nombre: str
    destino_renipress: str | None
    derivado_por: str | None
    descripcion: str | None
    categoria: CategoriaIncidencia | None
    estado: EstadoIncidencia
    motivo_archivo: MotivoArchivo | None


@dataclass(frozen=True, slots=True)
class DestinoDeDerivacion:
    codigo: str
    nombre: str
    codigo_renipress: str | None


@dataclass(frozen=True, slots=True)
class DerivacionResumen:
    id: str
    codigo_caso: str
    fecha_derivacion: str
    origen: AreaDeCaso
    destino: DestinoDeDerivacion
    derivado_por: str
    descripcion: str | None
    categoria: CategoriaApi | None
    estado: EstadoApi
    motivo_archivo: MotivoArchivo | None


@dataclass(frozen=True, slots=True)
class ConteosDeDerivaciones:
    todos: int
    pendientes: int
    en_gestion: int
    resueltos: int
    archivados: int


@dataclass(frozen=True, slots=True)
class DerivacionDetalle:
    derivacion: DerivacionResumen
    caso: CasoDetalle
