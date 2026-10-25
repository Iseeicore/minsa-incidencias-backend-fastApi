from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.incidencias.domain.casos import CasoDetalle


@dataclass(frozen=True, slots=True)
class ResultadoDeAccion:
    mensaje: str
    caso: CasoDetalle | None


@dataclass(frozen=True, slots=True)
class CasoEnviadoAOtrans:
    codigo: str
