from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import StrictBool, StringConstraints, model_validator
from pydantic_core import PydanticCustomError

from app.constants.incidencias import AREA_CODIGO_LONGITUD_MAXIMA
from app.constants.patrones import EMAIL_PATTERN
from app.constants.sesion import MAX_EMAIL_LENGTH
from app.constants.usuarios import (
    SIN_CAMBIOS_ERROR_TYPE,
    SIN_CAMBIOS_MENSAJE,
    USUARIO_NOMBRE_LONGITUD_MAXIMA,
    USUARIO_NOMBRE_LONGITUD_MINIMA,
)
from app.enums.rol_codigo import RolCodigo
from app.shared.api_model import ApiModel
from app.shared.pagina_response import PaginaResponse
from app.usuarios.domain.pedidos import CambiosDeUsuario, DatosNuevoUsuario

if TYPE_CHECKING:
    from app.shared.pagination import Pagina
    from app.usuarios.domain.pedidos import UsuarioConClave
    from app.usuarios.domain.usuario_gestionado import UsuarioGestionado

NombreCompleto = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=USUARIO_NOMBRE_LONGITUD_MINIMA, max_length=USUARIO_NOMBRE_LONGITUD_MAXIMA
    ),
]
Correo = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, max_length=MAX_EMAIL_LENGTH, pattern=EMAIL_PATTERN),
]
CodigoDeArea = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=AREA_CODIGO_LONGITUD_MAXIMA)
]
RolAsignable = Literal["ADMINISTRADOR", "GESTOR", "OTRANS", "ESTABLECIMIENTO"]


class AreaDeUsuarioResponse(ApiModel):
    codigo: str
    nombre: str


class UsuarioResponse(ApiModel):
    id: str
    nombre_completo: str
    correo: str
    rol: str | None
    activo: bool
    area: AreaDeUsuarioResponse | None

    @classmethod
    def desde_dominio(cls, usuario: UsuarioGestionado) -> Self:
        area = (
            AreaDeUsuarioResponse(codigo=usuario.area_codigo, nombre=usuario.area_nombre)
            if usuario.area_codigo and usuario.area_nombre
            else None
        )
        return cls(
            id=usuario.id,
            nombre_completo=usuario.nombre_completo,
            correo=usuario.correo,
            rol=usuario.rol,
            activo=usuario.activo,
            area=area,
        )


class PaginaDeUsuariosResponse(PaginaResponse[UsuarioResponse]):
    @classmethod
    def desde_dominio(cls, pagina: Pagina[UsuarioGestionado]) -> Self:
        return cls(
            items=[UsuarioResponse.desde_dominio(usuario) for usuario in pagina.items],
            siguiente=pagina.siguiente,
            hay_mas=pagina.hay_mas,
        )


class UsuarioConClaveResponse(ApiModel):
    usuario: UsuarioResponse
    clave_inicial: str

    @classmethod
    def desde_dominio(cls, creado: UsuarioConClave) -> Self:
        return cls(usuario=UsuarioResponse.desde_dominio(creado.usuario), clave_inicial=creado.clave_inicial)


class UsuarioActualizadoResponse(ApiModel):
    usuario: UsuarioResponse


class CreacionDeUsuarioRequest(ApiModel):
    nombre_completo: NombreCompleto
    correo: Correo
    rol: RolAsignable
    area: CodigoDeArea | None = None

    def a_dominio(self) -> DatosNuevoUsuario:
        return DatosNuevoUsuario(self.nombre_completo, self.correo, RolCodigo(self.rol), self.area)


class CambiosDeUsuarioRequest(ApiModel):
    nombre_completo: NombreCompleto | None = None
    rol: RolAsignable | None = None
    activo: StrictBool | None = None
    area: CodigoDeArea | None = None

    @model_validator(mode="after")
    def exigir_al_menos_un_cambio(self) -> Self:
        if not self.model_fields_set or all(getattr(self, campo) is None for campo in self.model_fields_set):
            raise PydanticCustomError(SIN_CAMBIOS_ERROR_TYPE, SIN_CAMBIOS_MENSAJE)
        return self

    def a_dominio(self) -> CambiosDeUsuario:
        rol = RolCodigo(self.rol) if self.rol is not None else None
        return CambiosDeUsuario(self.nombre_completo, rol, self.activo, self.area)
