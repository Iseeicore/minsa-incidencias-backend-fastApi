import pytest
from pydantic import ValidationError

from app.config.comandos import DatosDeAdministradorEnv, DatosDeUsuarioDePruebaEnv
from app.enums.rol_codigo import RolCodigo

CLAVE = "una-clave-larga-1"


def _entorno(monkeypatch: pytest.MonkeyPatch, prefijo: str, **valores: str) -> None:
    for nombre, valor in valores.items():
        monkeypatch.setenv(f"{prefijo}{nombre.upper()}", valor)


def test_el_administrador_se_lee_del_entorno_con_su_prefijo(monkeypatch: pytest.MonkeyPatch) -> None:
    _entorno(monkeypatch, "ADMIN_", nombre="  Ana Torres ", correo="ana@minsa.gob.pe", password=CLAVE)

    datos = DatosDeAdministradorEnv(_env_file=None)

    assert (datos.nombre, datos.correo, datos.password, datos.area) == ("Ana Torres", "ana@minsa.gob.pe", CLAVE, None)


def test_el_area_del_administrador_es_opcional_pero_no_puede_venir_vacia(monkeypatch: pytest.MonkeyPatch) -> None:
    _entorno(monkeypatch, "ADMIN_", nombre="Ana", correo="ana@minsa.gob.pe", password=CLAVE, area=" HOSP-01 ")
    assert DatosDeAdministradorEnv(_env_file=None).area == "HOSP-01"

    monkeypatch.setenv("ADMIN_AREA", "  ")
    with pytest.raises(ValidationError):
        DatosDeAdministradorEnv(_env_file=None)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("nombre", "   "), ("correo", "no-es-un-correo"), ("password", "corta")],
)
def test_un_dato_invalido_del_administrador_se_rechaza(monkeypatch: pytest.MonkeyPatch, campo: str, valor: str) -> None:
    validos = {"nombre": "Ana", "correo": "ana@minsa.gob.pe", "password": CLAVE}
    _entorno(monkeypatch, "ADMIN_", **{**validos, campo: valor})

    with pytest.raises(ValidationError) as error:
        DatosDeAdministradorEnv(_env_file=None)

    assert error.value.errors()[0]["loc"] == (campo,)


def test_si_falta_un_dato_del_administrador_se_rechaza(monkeypatch: pytest.MonkeyPatch) -> None:
    for nombre in ("ADMIN_NOMBRE", "ADMIN_CORREO", "ADMIN_PASSWORD", "ADMIN_AREA"):
        monkeypatch.delenv(nombre, raising=False)

    with pytest.raises(ValidationError) as error:
        DatosDeAdministradorEnv(_env_file=None)

    assert {e["loc"][0] for e in error.value.errors()} == {"nombre", "correo", "password"}


def test_el_usuario_de_prueba_lleva_ademas_su_rol(monkeypatch: pytest.MonkeyPatch) -> None:
    _entorno(
        monkeypatch, "USUARIO_", nombre="Gestor", correo="g@minsa.gob.pe", password=CLAVE, rol="GESTOR", area="HOSP-01"
    )

    datos = DatosDeUsuarioDePruebaEnv(_env_file=None)

    assert (datos.rol, datos.area) == (RolCodigo.GESTOR, "HOSP-01")


def test_un_rol_desconocido_del_usuario_de_prueba_se_rechaza(monkeypatch: pytest.MonkeyPatch) -> None:
    _entorno(monkeypatch, "USUARIO_", nombre="Gestor", correo="g@minsa.gob.pe", password=CLAVE, rol="SUPERUSUARIO")

    with pytest.raises(ValidationError) as error:
        DatosDeUsuarioDePruebaEnv(_env_file=None)

    assert error.value.errors()[0]["loc"] == ("rol",)
