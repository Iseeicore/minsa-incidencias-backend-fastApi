from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.filtro_corrupcion.domain.senales_guardadas import SenalesGuardadas


@dataclass(frozen=True, slots=True)
class CasoPendiente:
    id: str
    codigo: str
    descripcion: str
    establecimiento: str | None


@dataclass(frozen=True, slots=True)
class AnalisisAGuardar:
    incidencia_id: str
    version_reglas: str
    puntaje: int
    senales: SenalesGuardadas
    cargo_mencionado: str | None
    area_mencionada_id: int | None
    nombre_mencionado: str | None


@dataclass(frozen=True, slots=True)
class CategoriaAEscribir:
    incidencia_id: str
    categoria: CategoriaIncidencia
    confianza: float
    version: str


@dataclass(frozen=True, slots=True)
class FilaAlarma:
    atrasados: int
    minutos: float | None
    codigos: tuple[str, ...]
