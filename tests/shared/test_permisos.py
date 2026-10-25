import pytest

from app.enums.alcance_de_usuarios import AlcanceDeUsuarios
from app.enums.rol_codigo import RolCodigo
from app.enums.tarjeta_codigo import TarjetaCodigo
from app.enums.vista_codigo import VistaCodigo
from app.shared.permisos import (
    cuenta_todas_las_areas,
    gestion_de_usuarios,
    tarjetas_de_roles,
    ve_todas_las_areas,
    vistas_de_roles,
)

TODAS = tuple(VistaCodigo)


def test_el_administrador_ve_todas_las_vistas_en_el_orden_del_menu() -> None:
    assert vistas_de_roles(["ADMINISTRADOR"]) == TODAS


@pytest.mark.parametrize(
    ("rol", "faltan"),
    [
        ("GESTOR", {"DERIVACIONES", "QR", "USUARIOS", "CONSULTA_IPRESS"}),
        ("OTRANS", {"QR", "USUARIOS"}),
        ("ESTABLECIMIENTO", {"DERIVACIONES", "CONSULTA_IPRESS"}),
    ],
)
def test_cada_rol_ve_todas_las_vistas_menos_las_que_no_le_tocan(rol: str, faltan: set[str]) -> None:
    assert {vista.value for vista in TODAS} - {vista.value for vista in vistas_de_roles([rol])} == faltan


def test_varios_roles_suman_sus_vistas_sin_repetir_y_en_orden() -> None:
    vistas = vistas_de_roles(["OTRANS", "ESTABLECIMIENTO", "GESTOR"])

    assert list(vistas) == [vista for vista in TODAS if vista in set(vistas)]
    assert VistaCodigo.DERIVACIONES in vistas
    assert VistaCodigo.CONSULTA_IPRESS in vistas
    assert set(vistas) == set(TODAS)


def test_un_rol_desconocido_o_sin_permisos_no_suma_vistas() -> None:
    assert vistas_de_roles(["DIRIS", "NO_EXISTE"]) == ()


@pytest.mark.parametrize(
    ("rol", "esperado"), [("ADMINISTRADOR", True), ("GESTOR", True), ("OTRANS", False), ("ESTABLECIMIENTO", False)]
)
def test_quien_ve_todas_las_areas(rol: str, esperado: bool) -> None:  # noqa: FBT001
    assert ve_todas_las_areas([rol]) is esperado


def test_la_gestion_de_usuarios_del_administrador_es_total_y_asigna_cuatro_roles() -> None:
    gestion = gestion_de_usuarios(["ADMINISTRADOR"])

    assert gestion is not None
    assert gestion.alcance == AlcanceDeUsuarios.TODAS
    assert set(gestion.roles_asignables) == {
        RolCodigo.ADMINISTRADOR,
        RolCodigo.GESTOR,
        RolCodigo.OTRANS,
        RolCodigo.ESTABLECIMIENTO,
    }


def test_la_gestion_de_usuarios_del_establecimiento_se_limita_a_su_area() -> None:
    gestion = gestion_de_usuarios(["ESTABLECIMIENTO"])

    assert gestion is not None
    assert gestion.alcance == AlcanceDeUsuarios.SU_AREA
    assert gestion.roles_asignables == (RolCodigo.GESTOR, RolCodigo.ESTABLECIMIENTO)


@pytest.mark.parametrize("roles", [["ESTABLECIMIENTO", "ADMINISTRADOR"], ["ADMINISTRADOR", "ESTABLECIMIENTO"]])
def test_combinar_roles_gana_el_alcance_total(roles: list[str]) -> None:
    gestion = gestion_de_usuarios(roles)

    assert gestion is not None
    assert gestion.alcance == AlcanceDeUsuarios.TODAS
    assert len(gestion.roles_asignables) == len(set(gestion.roles_asignables)) == 4


@pytest.mark.parametrize("roles", [[], ["GESTOR"], ["OTRANS"], ["NO_EXISTE"]])
def test_sin_rol_que_gestione_usuarios_no_hay_gestion(roles: list[str]) -> None:
    assert gestion_de_usuarios(roles) is None


@pytest.mark.parametrize("rol", ["ADMINISTRADOR", "GESTOR", "OTRANS", "ESTABLECIMIENTO"])
def test_cada_rol_vigente_tiene_las_cuatro_tarjetas_del_tablero(rol: str) -> None:
    assert tarjetas_de_roles([rol]) == (
        TarjetaCodigo.RECIBIDOS,
        TarjetaCodigo.PENDIENTES,
        TarjetaCodigo.EN_GESTION,
        TarjetaCodigo.RESUELTOS,
    )


def test_varios_roles_no_repiten_tarjetas_y_un_rol_desconocido_no_suma() -> None:
    assert len(tarjetas_de_roles(["GESTOR", "OTRANS"])) == 4
    assert tarjetas_de_roles(["DIRIS", "NO_EXISTE"]) == ()


@pytest.mark.parametrize(
    ("roles", "esperado"),
    [(["ADMINISTRADOR"], True), (["GESTOR"], False), (["OTRANS", "ADMINISTRADOR"], True), (["NO_EXISTE"], False)],
)
def test_quien_cuenta_todas_las_areas(roles: list[str], esperado: bool) -> None:  # noqa: FBT001
    assert cuenta_todas_las_areas(roles) is esperado
