import pytest
from pydantic import ValidationError

from app.acceso.adapters.http.schemas import LoginRequest, PerfilDeSesionResponse
from app.enums.tipo_area import TipoArea
from tests.helpers.builders import un_area_de_sesion, una_sesion


@pytest.mark.parametrize(
    "correo",
    ["ana@minsa.gob.pe", "a.b+c@sub.dominio.pe", "x_y-z@a1.co", "O'Neil@minsa.gob.pe"],
)
def test_acepta_los_correos_que_acepta_zod(correo: str) -> None:
    assert LoginRequest(correo=correo, password="clave").correo == correo


@pytest.mark.parametrize(
    "correo",
    [
        "",
        "sin-arroba",
        "@minsa.gob.pe",
        "ana@",
        "ana@minsa",
        "ana@minsa.p",
        "ana @minsa.gob.pe",
        "ana@minsa.gob.pe\n",
        ".ana@minsa.gob.pe",
        "a..b@minsa.gob.pe",
        "ana@minsa.gob.pe.",
        "ñandu@minsa.gob.pe",
    ],
)
def test_rechaza_los_correos_que_rechaza_zod(correo: str) -> None:
    with pytest.raises(ValidationError):
        LoginRequest(correo=correo, password="clave")


@pytest.mark.parametrize("password", ["", "x" * 201])
def test_rechaza_una_clave_vacia_o_de_mas_de_200_caracteres(password: str) -> None:
    with pytest.raises(ValidationError):
        LoginRequest(correo="ana@minsa.gob.pe", password=password)


def test_acepta_una_clave_de_200_caracteres() -> None:
    assert len(LoginRequest(correo="ana@minsa.gob.pe", password="x" * 200).password) == 200


def test_el_perfil_trae_el_area_cuando_la_persona_la_tiene() -> None:
    sesion = una_sesion(roles=("ESTABLECIMIENTO",), area=un_area_de_sesion(tipo=TipoArea.ESTABLECIMIENTO))

    perfil = PerfilDeSesionResponse.desde_sesion(sesion).model_dump(by_alias=True, mode="json")

    assert perfil == {
        "nombreCompleto": "Gestor de Prueba",
        "correo": "gestor@minsa.gob.pe",
        "vistas": [vista.value for vista in sesion.vistas],
        "roles": ["ESTABLECIMIENTO"],
        "area": {"codigo": "HOSP-01", "nombre": "Hospital Uno", "tipo": "ESTABLECIMIENTO"},
    }


def test_el_perfil_sin_area_la_deja_nula() -> None:
    assert PerfilDeSesionResponse.desde_sesion(una_sesion()).area is None
