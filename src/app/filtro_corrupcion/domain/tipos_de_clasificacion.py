from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.estado_coincidencias import EstadoCoincidencias
    from app.enums.origen_clasificacion import OrigenClasificacion
    from app.filtro_corrupcion.domain.tipos import ResultadoCorrupcion, SenalQuejaReclamo


@dataclass(frozen=True, slots=True)
class CandidatoCoincidencia:
    categoria: CategoriaIncidencia
    similitud: float


@dataclass(frozen=True, slots=True)
class ResumenCoincidencias:
    estado: EstadoCoincidencias
    mejor: CandidatoCoincidencia | None
    margen: float | None


@dataclass(frozen=True, slots=True)
class ResultadoClasificacion:
    categoria: CategoriaIncidencia
    reglas: ResultadoCorrupcion
    senales_queja_reclamo: tuple[SenalQuejaReclamo, ...]
    requiere_revision_humana: bool
    revision_otrans: bool
    origen: OrigenClasificacion
    coincidencias: ResumenCoincidencias
