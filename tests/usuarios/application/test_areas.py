import pytest

from app.enums.rol_codigo import RolCodigo
from app.errors.no_procesable import NoProcesable
from app.errors.sin_permiso import SinPermiso
from app.shared.permisos import gestion_de_usuarios
from app.usuarios.application.areas import area_activa_o_error, area_para_crear
from app.usuarios.domain.pedidos import DatosNuevoUsuario
from tests.helpers.builders import un_area_de_sesion, una_sesion
from tests.helpers.usuarios_en_memoria import TransaccionEnMemoria, UsuariosEnMemoria


def _tx() -> TransaccionEnMemoria:
    return TransaccionEnMemoria(UsuariosEnMemoria())


async def test_un_area_activa_devuelve_su_id() -> None:
    assert await area_activa_o_error(_tx(), "HOSP-01") == 1


async def test_un_area_desconocida_es_no_procesable() -> None:
    with pytest.raises(NoProcesable):
        await area_activa_o_error(_tx(), "NO-EXISTE")


async def test_quien_gestiona_todas_las_areas_usa_el_area_pedida() -> None:
    gestion = gestion_de_usuarios(["ADMINISTRADOR"])
    assert gestion is not None

    area = await area_para_crear(
        _tx(),
        una_sesion(roles=("ADMINISTRADOR",)),
        gestion,
        DatosNuevoUsuario("A", "a@m.pe", RolCodigo.GESTOR, "HOSP-02"),
    )

    assert area == 2


async def test_quien_gestiona_su_area_usa_la_de_su_sesion() -> None:
    gestion = gestion_de_usuarios(["ESTABLECIMIENTO"])
    assert gestion is not None
    sesion = una_sesion(roles=("ESTABLECIMIENTO",), area=un_area_de_sesion(id=7))

    area = await area_para_crear(_tx(), sesion, gestion, DatosNuevoUsuario("A", "a@m.pe", RolCodigo.GESTOR, "HOSP-02"))

    assert area == 7


async def test_quien_gestiona_su_area_sin_tenerla_recibe_403() -> None:
    gestion = gestion_de_usuarios(["ESTABLECIMIENTO"])
    assert gestion is not None

    with pytest.raises(SinPermiso):
        await area_para_crear(
            _tx(), una_sesion(roles=("ESTABLECIMIENTO",)), gestion, DatosNuevoUsuario("A", "a@m.pe", RolCodigo.GESTOR)
        )
