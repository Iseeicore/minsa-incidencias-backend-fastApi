from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.enums.tipo_area import TipoArea
    from app.shared.cursor import PosicionPorNombre


@dataclass(frozen=True, slots=True)
class EstablecimientoDeArea:
    codigo_renipress: str
    nivel_atencion: str | None
    categoria: str | None


@dataclass(frozen=True, slots=True)
class AreaListada:
    id: int
    codigo: str
    nombre: str
    tipo_area: TipoArea
    establecimiento: EstablecimientoDeArea | None


@dataclass(frozen=True, slots=True)
class ConsultaAreas:
    limite: int
    despues_de: PosicionPorNombre[int] | None = None
    tipo: TipoArea | None = None
    texto: str | None = None


@dataclass(frozen=True, slots=True)
class FiltrosDeAreas:
    tipo: TipoArea | None = None
    texto: str | None = None
    solo_area_id: int | None = None
    restringir_a_un_area: bool = False
