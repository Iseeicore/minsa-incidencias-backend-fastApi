from typing import TYPE_CHECKING, Annotated, Self

from pydantic import StringConstraints

from app.constants.patrones import EMAIL_PATTERN
from app.constants.sesion import MAX_EMAIL_LENGTH, MAX_PASSWORD_LENGTH
from app.enums.tipo_area import TipoArea
from app.enums.vista_codigo import VistaCodigo
from app.shared.api_model import ApiModel

if TYPE_CHECKING:
    from app.shared.sesion import SesionActual


class LoginRequest(ApiModel):
    correo: Annotated[str, StringConstraints(max_length=MAX_EMAIL_LENGTH, pattern=EMAIL_PATTERN)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=MAX_PASSWORD_LENGTH)]


class AreaDeSesionResponse(ApiModel):
    codigo: str
    nombre: str
    tipo: TipoArea


class PerfilDeSesionResponse(ApiModel):
    nombre_completo: str
    correo: str
    vistas: list[VistaCodigo]
    roles: list[str]
    area: AreaDeSesionResponse | None

    @classmethod
    def desde_sesion(cls, sesion: SesionActual) -> Self:
        area = (
            AreaDeSesionResponse(codigo=sesion.area.codigo, nombre=sesion.area.nombre, tipo=sesion.area.tipo)
            if sesion.area is not None
            else None
        )
        return cls(
            nombre_completo=sesion.nombre_completo,
            correo=sesion.correo,
            vistas=list(sesion.vistas),
            roles=list(sesion.roles),
            area=area,
        )
