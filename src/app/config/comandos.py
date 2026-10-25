from typing import Annotated

from pydantic import StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants.patrones import EMAIL_PATTERN
from app.constants.sesion import MAX_EMAIL_LENGTH
from app.constants.usuarios import CLAVE_MINIMA_DE_COMANDO
from app.enums.rol_codigo import RolCodigo

type Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type Correo = Annotated[str, StringConstraints(max_length=MAX_EMAIL_LENGTH, pattern=EMAIL_PATTERN)]
type Clave = Annotated[str, StringConstraints(min_length=CLAVE_MINIMA_DE_COMANDO)]

PREFIJO_DE_ADMINISTRADOR = "ADMIN_"
PREFIJO_DE_USUARIO_DE_PRUEBA = "USUARIO_"


class DatosDeAdministradorEnv(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=PREFIJO_DE_ADMINISTRADOR, env_file=".env", extra="ignore", regex_engine="python-re"
    )

    nombre: Nombre
    correo: Correo
    password: Clave
    area: Nombre | None = None


class DatosDeUsuarioDePruebaEnv(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=PREFIJO_DE_USUARIO_DE_PRUEBA, env_file=".env", extra="ignore", regex_engine="python-re"
    )

    nombre: Nombre
    correo: Correo
    password: Clave
    rol: RolCodigo
    area: Nombre | None = None
