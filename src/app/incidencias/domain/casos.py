from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.enums.accion_incidencia import AccionIncidencia
    from app.enums.categoria_api import CategoriaApi
    from app.enums.estado_api import EstadoApi
    from app.enums.motivo_archivo import MotivoArchivo
    from app.enums.resultado_resolucion import ResultadoResolucion
    from app.incidencias.domain.fila_historial import ItemDeHistorial
    from app.incidencias.domain.plazo import PlazoCalculado


@dataclass(frozen=True, slots=True)
class AreaDeCaso:
    codigo: str
    nombre: str


@dataclass(frozen=True, slots=True)
class EstablecimientoDeCaso:
    codigo_renipress: str
    nombre: str
    nivel_atencion: str | None
    categoria: str | None


@dataclass(frozen=True, slots=True)
class CasoResumen:
    codigo: str
    categoria: CategoriaApi | None
    categoria_ia: CategoriaApi | None
    confianza_ia: float | None
    area: AreaDeCaso | None
    establecimiento: EstablecimientoDeCaso | None
    responsable: str | None
    estado: EstadoApi
    horas_desde_llegada: int
    horas_desde_resolucion: int | None
    revisado_por_humano: bool
    corregida: bool
    plazo: PlazoCalculado
    acciones: tuple[AccionIncidencia, ...]


@dataclass(frozen=True, slots=True)
class EvidenciaDeCaso:
    id: str
    nombre: str
    tipo: str
    fecha: str
    sensible: bool
    verificada: bool
    contenido_disponible: bool


@dataclass(frozen=True, slots=True)
class ResolucionDeCaso:
    medidas_tomadas: str
    fundamento: str
    resultado: ResultadoResolucion


@dataclass(frozen=True, slots=True)
class ArchivoDeCaso:
    motivo: MotivoArchivo
    detalle: str | None
    archivado_en: str


@dataclass(frozen=True, slots=True)
class ReaperturaDeCaso:
    reabierto_en: str
    motivo: str


@dataclass(frozen=True, slots=True)
class CasoDetalle:
    resumen: CasoResumen
    descripcion_derivacion: str | None
    resolucion: ResolucionDeCaso | None
    archivo: ArchivoDeCaso | None
    reapertura: ReaperturaDeCaso | None
    descripcion: str
    reclamante: str
    evidencias: tuple[EvidenciaDeCaso, ...]
    historial: tuple[ItemDeHistorial, ...]


@dataclass(frozen=True, slots=True)
class ConteoAcotado:
    cantidad: int
    con_mas: bool


@dataclass(frozen=True, slots=True)
class ConteosDeCasos:
    todos: ConteoAcotado
    total: ConteoAcotado
    por_estado: dict[EstadoApi, ConteoAcotado]


@dataclass(frozen=True, slots=True)
class CasosPorVencer:
    total: int
    por_vencer: int
    vencidos: int
    casos: tuple[CasoResumen, ...]
