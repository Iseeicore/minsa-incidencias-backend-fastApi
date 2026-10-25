import pytest

from app.enums.rol_codigo import RolCodigo
from app.errors.no_encontrado import NoEncontrado
from app.errors.sin_permiso import SinPermiso
from app.shared.permisos import gestion_de_usuarios
from app.usuarios.domain.gestion import exigir_gestion, exigir_rol_asignable, restriccion_de, usuario_no_encontrado
from app.usuarios.domain.pedidos import RestriccionDeArea
from tests.helpers.builders import un_area_de_sesion, una_sesion


def test_exigir_gestion_devuelve_la_gestion_del_rol() -> None:
    assert exigir_gestion(["ADMINISTRADOR"]) == gestion_de_usuarios(["ADMINISTRADOR"])


@pytest.mark.parametrize("roles", [[], ["GESTOR"], ["OTRANS"]])
def test_exigir_gestion_sin_rol_que_gestione_usuarios_es_403(roles: list[str]) -> None:
    with pytest.raises(SinPermiso):
        exigir_gestion(roles)


def test_un_rol_asignable_pasa_y_uno_no_asignable_es_403() -> None:
    gestion = exigir_gestion(["ESTABLECIMIENTO"])

    exigir_rol_asignable(gestion, RolCodigo.GESTOR)
    with pytest.raises(SinPermiso, match="No puedes asignar ese rol"):
        exigir_rol_asignable(gestion, RolCodigo.ADMINISTRADOR)


def test_quien_gestiona_todo_no_tiene_restriccion_de_area() -> None:
    sesion = una_sesion(roles=("ADMINISTRADOR",))

    assert restriccion_de(sesion, exigir_gestion(sesion.roles)) is None


def test_quien_gestiona_su_area_queda_restringido_a_ella_o_a_ninguna() -> None:
    con_area = una_sesion(roles=("ESTABLECIMIENTO",), area=un_area_de_sesion(id=4))
    sin_area = una_sesion(roles=("ESTABLECIMIENTO",))

    assert restriccion_de(con_area, exigir_gestion(con_area.roles)) == RestriccionDeArea(4)
    assert restriccion_de(sin_area, exigir_gestion(sin_area.roles)) == RestriccionDeArea(None)


def test_el_usuario_no_encontrado_lleva_el_mensaje_del_contrato() -> None:
    error = usuario_no_encontrado()

    assert isinstance(error, NoEncontrado)
    assert error.message == "El usuario solicitado no existe."
