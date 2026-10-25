from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.enums.categoria_incidencia import CategoriaIncidencia


@dataclass(frozen=True, slots=True)
class PlazoDeCategoria:
    categoria: CategoriaIncidencia
    plazo_dias_habiles: int
    archiva_por_vencimiento: bool
