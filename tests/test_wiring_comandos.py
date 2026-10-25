import pytest

from app.config.settings import Settings
from app.shared.database import create_engine
from app.usuarios.application.crear_administrador import CrearAdministrador
from app.usuarios.application.crear_usuario_de_prueba import CrearUsuarioDePrueba
from app.wiring import build_crear_administrador, build_crear_usuario_de_prueba


async def test_los_comandos_de_usuarios_se_arman_sobre_la_base_y_el_hasher_real(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:c@localhost:1/b")
    monkeypatch.setenv("COOKIE_SECRET", "s" * 32)
    engine = create_engine(Settings(_env_file=None))

    assert isinstance(build_crear_administrador(engine), CrearAdministrador)
    assert isinstance(build_crear_usuario_de_prueba(engine), CrearUsuarioDePrueba)
    await engine.dispose()
