from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from app.enums.tipo_area import TipoArea
    from app.enums.vista_codigo import VistaCodigo
    from app.shared.ports import ControlDeSesion


@dataclass(frozen=True, slots=True)
class AreaDeSesion:
    id: int
    codigo: str
    nombre: str
    tipo: TipoArea


@dataclass(frozen=True, slots=True)
class VigenciaDeSesion:
    vence_en: datetime
    inactiva_en: datetime


@dataclass(frozen=True, slots=True)
class SesionActual:
    sesion_id: str
    usuario_id: str
    correo: str
    nombre_completo: str
    roles: tuple[str, ...]
    area: AreaDeSesion | None = None
    vistas: tuple[VistaCodigo, ...] = ()
    vigencia: VigenciaDeSesion | None = None
    control_eventos: ControlDeSesion | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class SesionEnVivo:
    sesion_id: str
    usuario_id: str
    roles: tuple[str, ...]
    area_id: int | None
    vigencia: VigenciaDeSesion
    control: ControlDeSesion
