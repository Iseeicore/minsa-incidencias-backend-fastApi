import pytest
from pydantic import ValidationError

from app.enums.rol_codigo import RolCodigo
from app.shared.pagination import Pagina
from app.usuarios.adapters.http.schemas import (
    CambiosDeUsuarioRequest,
    CreacionDeUsuarioRequest,
    PaginaDeUsuariosResponse,
    UsuarioConClaveResponse,
    UsuarioResponse,
)
from app.usuarios.domain.pedidos import CambiosDeUsuario, DatosNuevoUsuario, UsuarioConClave
from tests.helpers.builders import un_usuario_gestionado

BASE = {"nombreCompleto": "  Dora Nueva  ", "correo": "  DORA@Minsa.gob.pe ", "rol": "GESTOR", "area": " HOSP-01 "}


def test_la_creacion_recorta_el_nombre_el_area_y_normaliza_el_correo() -> None:
    datos = CreacionDeUsuarioRequest.model_validate(BASE).a_dominio()

    assert datos == DatosNuevoUsuario("Dora Nueva", "dora@minsa.gob.pe", RolCodigo.GESTOR, "HOSP-01")


def test_el_area_es_opcional_al_crear() -> None:
    assert CreacionDeUsuarioRequest.model_validate({**BASE, "area": None}).a_dominio().area is None


@pytest.mark.parametrize(
    "cambio",
    [
        {"nombreCompleto": "ab"},
        {"nombreCompleto": "x" * 121},
        {"nombreCompleto": "   "},
        {"correo": "x" * 250 + "@minsa.gob.pe"},
        {"correo": "malo"},
        {"rol": "DIRIS"},
        {"rol": "gestor"},
        {"area": "   "},
        {"area": "x" * 51},
    ],
)
def test_la_creacion_rechaza_datos_fuera_del_contrato(cambio: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        CreacionDeUsuarioRequest.model_validate({**BASE, **cambio})


def test_la_creacion_ignora_campos_desconocidos() -> None:
    assert CreacionDeUsuarioRequest.model_validate({**BASE, "otro": 1}).nombre_completo == "Dora Nueva"


def test_los_cambios_llevan_solo_lo_indicado() -> None:
    cambios = CambiosDeUsuarioRequest.model_validate({"activo": False, "rol": "OTRANS"}).a_dominio()

    assert cambios == CambiosDeUsuario(rol=RolCodigo.OTRANS, activo=False)


@pytest.mark.parametrize("cuerpo", [{}, {"activo": None}, {"nombreCompleto": None, "area": None}])
def test_los_cambios_exigen_al_menos_un_dato(cuerpo: dict[str, None]) -> None:
    with pytest.raises(ValidationError, match=r"Indica al menos un dato para cambiar\."):
        CambiosDeUsuarioRequest.model_validate(cuerpo)


@pytest.mark.parametrize("activo", ["true", 1, "si"])
def test_activo_solo_acepta_booleanos(activo: object) -> None:
    with pytest.raises(ValidationError):
        CambiosDeUsuarioRequest.model_validate({"activo": activo})


def test_la_respuesta_del_usuario_trae_el_area_solo_si_la_tiene() -> None:
    con_area = UsuarioResponse.desde_dominio(un_usuario_gestionado()).model_dump(by_alias=True)
    sin_area = UsuarioResponse.desde_dominio(un_usuario_gestionado(area_id=None, rol="ADMINISTRADOR"))

    assert con_area["area"] == {"codigo": "HOSP-01", "nombre": "Hospital Uno"}
    assert con_area["nombreCompleto"] == "Ana Torres"
    assert sin_area.area is None


def test_la_pagina_y_la_clave_inicial_se_arman_desde_el_dominio() -> None:
    usuario = un_usuario_gestionado()

    pagina = PaginaDeUsuariosResponse.desde_dominio(Pagina([usuario], "cursor", hay_mas=True))
    con_clave = UsuarioConClaveResponse.desde_dominio(UsuarioConClave(usuario, "clave"))

    assert pagina.model_dump(by_alias=True)["hayMas"] is True
    assert pagina.siguiente == "cursor"
    assert (con_clave.clave_inicial, con_clave.usuario.id) == ("clave", usuario.id)
