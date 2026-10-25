from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.shared.cursor import PosicionPorNombre


@dataclass(frozen=True, slots=True)
class IpressConsultada:
    establecimiento_id: int
    codigo: str
    nombre: str


@dataclass(frozen=True, slots=True)
class IpressListada:
    id: int
    codigo: str
    nombre: str
    codigo_renipress: str
    nivel_atencion: str | None
    categoria: str | None


@dataclass(frozen=True, slots=True)
class ConsultaDeIpress:
    limite: int
    despues_de: PosicionPorNombre[int] | None = None
    texto: str | None = None
