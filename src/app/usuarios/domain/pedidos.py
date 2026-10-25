from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.enums.rol_codigo import RolCodigo
    from app.shared.cursor import PosicionPorNombre
    from app.usuarios.domain.usuario_gestionado import UsuarioGestionado


@dataclass(frozen=True, slots=True)
class ConsultaUsuarios:
    limite: int
    despues_de: PosicionPorNombre[str] | None = None
    texto: str | None = None
    area: str | None = None


@dataclass(frozen=True, slots=True)
class DatosNuevoUsuario:
    nombre_completo: str
    correo: str
    rol: RolCodigo
    area: str | None = None


@dataclass(frozen=True, slots=True)
class CambiosDeUsuario:
    nombre_completo: str | None = None
    rol: RolCodigo | None = None
    activo: bool | None = None
    area: str | None = None


@dataclass(frozen=True, slots=True)
class RestriccionDeArea:
    area_id: int | None


@dataclass(frozen=True, slots=True)
class FiltrosDeUsuarios:
    texto: str | None = None
    area_codigo: str | None = None
    restriccion_de_area: RestriccionDeArea | None = None


@dataclass(frozen=True, slots=True)
class NuevoUsuarioFila:
    nombre_completo: str
    correo: str
    huella: str
    area_id: int | None


@dataclass(frozen=True, slots=True)
class UsuarioConClave:
    usuario: UsuarioGestionado
    clave_inicial: str


@dataclass(frozen=True, slots=True)
class DatosDeAdministrador:
    nombre_completo: str
    correo: str
    password: str
    area: str | None = None


@dataclass(frozen=True, slots=True)
class DatosDeUsuarioDePrueba:
    nombre_completo: str
    correo: str
    password: str
    rol: RolCodigo
    area: str | None = None
