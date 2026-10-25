import sys
from typing import TYPE_CHECKING

from pydantic import ValidationError

from app.config.comandos import (
    PREFIJO_DE_ADMINISTRADOR,
    PREFIJO_DE_USUARIO_DE_PRUEBA,
    DatosDeAdministradorEnv,
    DatosDeUsuarioDePruebaEnv,
)
from app.config.settings import get_settings
from app.constants.salida import CODIGO_DE_SALIDA_CORRECTO, CODIGO_DE_SALIDA_FALLIDO
from app.constants.textos.usuarios import (
    MENSAJE_ADMINISTRADOR_CREADO,
    MENSAJE_USUARIO_DE_PRUEBA_CREADO,
    MENSAJE_USUARIO_DE_PRUEBA_EXISTENTE,
)
from app.enums.resultado_usuario_de_prueba import ResultadoUsuarioDePrueba
from app.shared.base_desechable import asegurar_base_desechable
from app.shared.bucle import ejecutar_corutina
from app.shared.correo import normalizar_correo
from app.shared.database import create_engine
from app.usuarios.domain.pedidos import DatosDeAdministrador, DatosDeUsuarioDePrueba
from app.wiring import build_crear_administrador, build_crear_usuario_de_prueba

if TYPE_CHECKING:
    from app.config.settings import Settings


def _informar_validacion(error: ValidationError, prefijo: str) -> int:
    for problema in error.errors():
        campo = ".".join(str(parte) for parte in problema["loc"])
        sys.stderr.write(f"{prefijo}{campo.upper()}: {problema['msg']}\n")
    return CODIGO_DE_SALIDA_FALLIDO


async def crear_administrador(settings: Settings, datos: DatosDeAdministrador) -> int:
    engine = create_engine(settings)
    try:
        await build_crear_administrador(engine).execute(datos)
        sys.stdout.write(MENSAJE_ADMINISTRADOR_CREADO.format(correo=normalizar_correo(datos.correo)))
    except Exception as error:  # noqa: BLE001
        sys.stderr.write(f"{error}\n")
        return CODIGO_DE_SALIDA_FALLIDO
    finally:
        await engine.dispose()
    return CODIGO_DE_SALIDA_CORRECTO


async def crear_usuario_de_prueba(settings: Settings, datos: DatosDeUsuarioDePrueba) -> int:
    engine = create_engine(settings)
    try:
        asegurar_base_desechable(settings.database_url.get_secret_value())
        resultado = await build_crear_usuario_de_prueba(engine).execute(datos)
        correo = normalizar_correo(datos.correo)
        if resultado == ResultadoUsuarioDePrueba.CREADO:
            sys.stdout.write(MENSAJE_USUARIO_DE_PRUEBA_CREADO.format(correo=correo, rol=datos.rol.value))
        else:
            sys.stdout.write(MENSAJE_USUARIO_DE_PRUEBA_EXISTENTE.format(correo=correo))
    except Exception as error:  # noqa: BLE001
        sys.stderr.write(f"{error}\n")
        return CODIGO_DE_SALIDA_FALLIDO
    finally:
        await engine.dispose()
    return CODIGO_DE_SALIDA_CORRECTO


def ejecutar_crear_administrador() -> int:
    try:
        settings = get_settings()
    except ValidationError as error:
        return _informar_validacion(error, "")
    try:
        entorno = DatosDeAdministradorEnv()
    except ValidationError as error:
        return _informar_validacion(error, PREFIJO_DE_ADMINISTRADOR)
    datos = DatosDeAdministrador(entorno.nombre, entorno.correo, entorno.password, entorno.area)
    return ejecutar_corutina(crear_administrador(settings, datos))


def ejecutar_crear_usuario_de_prueba() -> int:
    try:
        settings = get_settings()
    except ValidationError as error:
        return _informar_validacion(error, "")
    try:
        entorno = DatosDeUsuarioDePruebaEnv()
    except ValidationError as error:
        return _informar_validacion(error, PREFIJO_DE_USUARIO_DE_PRUEBA)
    datos = DatosDeUsuarioDePrueba(entorno.nombre, entorno.correo, entorno.password, entorno.rol, entorno.area)
    return ejecutar_corutina(crear_usuario_de_prueba(settings, datos))
