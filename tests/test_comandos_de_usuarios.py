import os
import uuid
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.comandos_de_usuarios import (
    crear_administrador,
    crear_usuario_de_prueba,
    ejecutar_crear_administrador,
    ejecutar_crear_usuario_de_prueba,
)
from app.config.settings import Settings, get_settings
from app.constants.salida import CODIGO_DE_SALIDA_CORRECTO, CODIGO_DE_SALIDA_FALLIDO
from app.enums.rol_codigo import RolCodigo
from app.shared.password_hasher import Argon2PasswordHasher
from app.usuarios.domain.pedidos import DatosDeAdministrador, DatosDeUsuarioDePrueba
from tests.helpers.base import consultar, sembrar_area

CLAVE = "una-clave-larga-1"
PLANTILLA = "bd_plantilla_desechable"


def _settings(url: str) -> Settings:
    return Settings(_env_file=None, database_url=url, cookie_secret="s" * 32, node_env="development")


def _url_de(engine: AsyncEngine) -> str:
    return engine.url.set(drivername="postgresql").render_as_string(hide_password=False)


@pytest.fixture
async def base_desechable() -> AsyncIterator[str]:
    admin_url = make_url(os.environ["TEST_DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1))
    nombre = f"comandos_{uuid.uuid4().hex}_desechable"
    admin = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conexion:
        await conexion.execute(text(f'CREATE DATABASE "{nombre}" TEMPLATE "{PLANTILLA}"'))
    yield admin_url.set(database=nombre, drivername="postgresql").render_as_string(hide_password=False)
    async with admin.connect() as conexion:
        await conexion.execute(text(f'DROP DATABASE "{nombre}" WITH (FORCE)'))
    await admin.dispose()


@pytest.mark.integration
async def test_crea_al_administrador_en_la_base_con_su_rol_y_una_huella_que_verifica(
    engine: AsyncEngine, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo = await crear_administrador(
        _settings(_url_de(engine)), DatosDeAdministrador("Ana Torres", " ANA@Minsa.GOB.pe", CLAVE)
    )

    [(nombre, correo, huella, rol, area)] = await consultar(
        engine,
        "SELECT u.nombre_completo, u.correo, u.password_hash, r.codigo, u.area_id FROM gestion.usuario_interno u"
        " JOIN gestion.usuario_rol ur ON ur.usuario_interno_id = u.id JOIN gestion.rol r ON r.id = ur.rol_id",
    )
    assert codigo == CODIGO_DE_SALIDA_CORRECTO
    assert (nombre, correo, rol, area) == ("Ana Torres", "ana@minsa.gob.pe", "ADMINISTRADOR", None)
    assert await Argon2PasswordHasher().verify(str(huella), CLAVE)
    assert capsys.readouterr().out == "Administrador creado: ana@minsa.gob.pe\n"


@pytest.mark.integration
async def test_un_correo_repetido_o_un_area_inexistente_terminan_con_error_y_mensaje(
    engine: AsyncEngine, capsys: pytest.CaptureFixture[str]
) -> None:
    await sembrar_area(engine, 10, "HOSP-01", "Hospital Uno")
    settings = _settings(_url_de(engine))
    await crear_administrador(settings, DatosDeAdministrador("Ana", "ana@minsa.gob.pe", CLAVE, "HOSP-01"))
    capsys.readouterr()

    repetido = await crear_administrador(settings, DatosDeAdministrador("Otra", "ANA@minsa.gob.pe", CLAVE))
    sin_area = await crear_administrador(
        settings, DatosDeAdministrador("Luis", "luis@minsa.gob.pe", CLAVE, "NO-EXISTE")
    )

    errores = capsys.readouterr().err
    assert (repetido, sin_area) == (CODIGO_DE_SALIDA_FALLIDO, CODIGO_DE_SALIDA_FALLIDO)
    assert errores == "Ya existe un usuario con ese correo.\nNo existe un área activa con el código NO-EXISTE.\n"


@pytest.mark.integration
async def test_el_usuario_de_prueba_se_niega_a_correr_contra_una_base_que_no_es_desechable(
    engine: AsyncEngine, capsys: pytest.CaptureFixture[str]
) -> None:
    datos = DatosDeUsuarioDePrueba("Gestor", "gestor@minsa.gob.pe", CLAVE, RolCodigo.GESTOR)

    codigo = await crear_usuario_de_prueba(_settings(_url_de(engine)), datos)

    assert codigo == CODIGO_DE_SALIDA_FALLIDO
    assert "base desechable" in capsys.readouterr().err
    assert await consultar(engine, "SELECT 1 FROM gestion.usuario_interno") == []


@pytest.mark.integration
async def test_el_usuario_de_prueba_se_crea_una_vez_y_la_segunda_se_deja_como_estaba(
    base_desechable: str, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = _settings(base_desechable)
    datos = DatosDeUsuarioDePrueba("Gestor", "GESTOR@minsa.gob.pe", CLAVE, RolCodigo.ADMINISTRADOR)

    primero = await crear_usuario_de_prueba(settings, datos)
    segundo = await crear_usuario_de_prueba(settings, datos)

    assert (primero, segundo) == (CODIGO_DE_SALIDA_CORRECTO, CODIGO_DE_SALIDA_CORRECTO)
    assert capsys.readouterr().out == (
        "Usuario de prueba creado: gestor@minsa.gob.pe (ADMINISTRADOR)\n"
        "El usuario ya existía y se dejó como estaba: gestor@minsa.gob.pe\n"
    )


@pytest.mark.parametrize(
    ("ejecutar", "prefijo"),
    [(ejecutar_crear_administrador, "ADMIN_"), (ejecutar_crear_usuario_de_prueba, "USUARIO_")],
    ids=["administrador", "usuario-de-prueba"],
)
def test_si_faltan_datos_cada_campo_se_informa_con_su_variable_y_termina_con_error(
    ejecutar: Callable[[], int],
    prefijo: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:c@127.0.0.1:1/b_desechable")
    monkeypatch.setenv("COOKIE_SECRET", "s" * 32)
    for sufijo in ("NOMBRE", "CORREO", "PASSWORD", "AREA", "ROL"):
        monkeypatch.delenv(f"{prefijo}{sufijo}", raising=False)
    get_settings.cache_clear()

    codigo = ejecutar()

    get_settings.cache_clear()
    errores = capsys.readouterr().err
    assert codigo == CODIGO_DE_SALIDA_FALLIDO
    assert f"{prefijo}NOMBRE: Field required" in errores
    assert f"{prefijo}CORREO: Field required" in errores
    assert f"{prefijo}PASSWORD: Field required" in errores


def test_si_falta_la_configuracion_del_servicio_tambien_termina_con_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("COOKIE_SECRET", raising=False)
    get_settings.cache_clear()

    codigo = ejecutar_crear_administrador()

    get_settings.cache_clear()
    assert codigo == CODIGO_DE_SALIDA_FALLIDO
    errores = capsys.readouterr().err
    assert "DATABASE_URL: Field required" in errores
    assert "COOKIE_SECRET: Field required" in errores
