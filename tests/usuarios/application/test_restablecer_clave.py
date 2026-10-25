import pytest

from app.errors.no_encontrado import NoEncontrado
from app.errors.sin_permiso import SinPermiso
from app.usuarios.application.restablecer_clave import RestablecerClave
from tests.helpers.acceso_en_memoria import HasherFalso
from tests.helpers.builders import un_area_de_sesion, un_usuario_gestionado, una_sesion
from tests.helpers.usuarios_en_memoria import UsuariosEnMemoria

ANA = "11111111-1111-4111-8111-111111111111"
BRUNO = "22222222-2222-4222-8222-222222222222"
ADMIN = una_sesion(correo="admin@minsa.gob.pe", roles=("ADMINISTRADOR",))


def _caso() -> tuple[RestablecerClave, UsuariosEnMemoria, HasherFalso]:
    almacen = UsuariosEnMemoria([un_usuario_gestionado(ANA, area_id=1), un_usuario_gestionado(BRUNO, area_id=2)])
    hasher = HasherFalso()
    return RestablecerClave(almacen, hasher), almacen, hasher


async def test_restablecer_guarda_la_huella_nueva_cierra_las_sesiones_y_devuelve_la_clave() -> None:
    caso, almacen, hasher = _caso()

    resultado = await caso.execute(ADMIN, ANA)

    assert len(resultado.clave_inicial) == 20
    assert hasher.hashes == [resultado.clave_inicial]
    assert almacen.huellas[ANA] == f"hash:{resultado.clave_inicial}"
    assert almacen.sesiones_cerradas == [ANA]
    assert resultado.usuario.id == ANA
    assert almacen.actores == ["usuario:admin@minsa.gob.pe"]


async def test_un_usuario_inexistente_responde_404() -> None:
    caso, almacen, _ = _caso()

    with pytest.raises(NoEncontrado):
        await caso.execute(ADMIN, "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69")

    assert almacen.sesiones_cerradas == []


async def test_el_establecimiento_solo_restablece_en_su_area() -> None:
    caso, almacen, _ = _caso()
    jefe = una_sesion(roles=("ESTABLECIMIENTO",), area=un_area_de_sesion(id=1))

    await caso.execute(jefe, ANA)
    with pytest.raises(NoEncontrado):
        await caso.execute(jefe, BRUNO)

    assert almacen.sesiones_cerradas == [ANA]


async def test_quien_no_gestiona_usuarios_recibe_403() -> None:
    caso, almacen, hasher = _caso()

    with pytest.raises(SinPermiso):
        await caso.execute(una_sesion(roles=("GESTOR",)), ANA)

    assert hasher.hashes == []
    assert almacen.huellas == {}
