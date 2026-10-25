from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.shared.sesion import AreaDeSesion, VigenciaDeSesion


@dataclass(frozen=True, slots=True)
class SesionVigente:
    sesion_id: str
    usuario_id: str
    correo: str
    nombre_completo: str
    roles: tuple[str, ...]
    area: AreaDeSesion | None
    debe_tocar: bool
    vigencia: VigenciaDeSesion
