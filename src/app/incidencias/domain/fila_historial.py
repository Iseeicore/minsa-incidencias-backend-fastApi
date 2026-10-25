from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.estado_incidencia import EstadoIncidencia


@dataclass(frozen=True, slots=True)
class FilaHistorial:
    operacion: str
    actor: str
    actor_nombre: str | None
    fecha_hora: datetime
    ia: bool
    categoria_ia: CategoriaIncidencia | None
    confianza: float | None
    version: str | None
    corregida: bool
    categoria_antes: CategoriaIncidencia | None
    categoria_despues: CategoriaIncidencia | None
    confirmada: bool
    estado_nuevo: EstadoIncidencia | None
    area_antes: str | None
    area_despues: str | None
    descripcion_derivacion: str | None
    resolvio: bool
    reabrio: bool


@dataclass(frozen=True, slots=True)
class ItemDeHistorial:
    titulo: str
    detalle: str
    hora: str
    fecha: str
