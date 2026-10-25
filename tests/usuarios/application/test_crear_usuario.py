import pytest

from app.enums.rol_codigo import RolCodigo
from app.errors.correo_repetido import CorreoRepetido
from app.errors.no_procesable import NoProcesable
from app.errors.sin_permiso import SinPermiso
from app.usuarios.application.crear_usuario import CrearUsuario
from app.usuarios.domain.pedidos import DatosNuevoUsuario
from tests.helpers.acceso_en_memoria import HasherFalso
from tests.helpers.builders import un_area_de_sesion, un_usuario_gestionado, una_sesion
from tests.helpers.usuarios_en_memoria import UsuariosEnMemoria

ADMIN = una_sesion(correo="admin@minsa.gob.pe", roles=("ADMINISTRADOR",))
ESTABLECIMIENTO = una_sesion(correo="jefe@minsa.gob.pe", roles=("ESTABLECIMIENTO",), area=un_area_de_sesion(id=1))


def _caso(almacen: UsuariosEnMemoria | None = None) -> tuple[CrearUsuario, UsuariosEnMemoria, HasherFalso]:
    almacen = almacen or UsuariosEnMemoria()
    hasher = HasherFalso()
    return CrearUsuario(almacen, hasher), almacen, hasher


async def test_el_administrador_crea_un_usuario_con_area_y_recibe_la_clave_inicial_una_vez() -> None:
    caso, almacen, hasher = _caso()

    creado = await caso.execute(
        ADMIN, DatosNuevoUsuario("Dora Nueva", "dora@minsa.gob.pe", RolCodigo.GESTOR, "HOSP-02")
    )

    assert (creado.usuario.nombre_completo, creado.usuario.rol, creado.usuario.area_codigo) == (
        "Dora Nueva",
        "GESTOR",
        "HOSP-02",
    )
    assert len(creado.clave_inicial) == 20
    assert hasher.hashes == [creado.clave_inicial]
    assert almacen.huellas[creado.usuario.id] == f"hash:{creado.clave_inicial}"
    assert almacen.actores == ["usuario:admin@minsa.gob.pe"]


async def test_el_administrador_se_crea_sin_area() -> None:
    caso, _, _ = _caso()

    creado = await caso.execute(ADMIN, DatosNuevoUsuario("Otro Admin", "otro@minsa.gob.pe", RolCodigo.ADMINISTRADOR))

    assert (creado.usuario.rol, creado.usuario.area_id) == ("ADMINISTRADOR", None)


async def test_un_administrador_con_area_es_no_procesable() -> None:
    caso, almacen, _ = _caso()

    with pytest.raises(NoProcesable, match="no indiques el área"):
        await caso.execute(
            ADMIN, DatosNuevoUsuario("Otro Admin", "otro@minsa.gob.pe", RolCodigo.ADMINISTRADOR, "HOSP-01")
        )

    assert almacen.usuarios == {}


async def test_un_rol_que_no_es_administrador_exige_area() -> None:
    caso, _, _ = _caso()

    with pytest.raises(NoProcesable, match="Indica el área"):
        await caso.execute(ADMIN, DatosNuevoUsuario("Dora", "dora@minsa.gob.pe", RolCodigo.GESTOR))


@pytest.mark.parametrize("area", ["NO-EXISTE"])
async def test_un_area_inexistente_es_no_procesable(area: str) -> None:
    caso, _, _ = _caso()

    with pytest.raises(NoProcesable, match="no existe o está desactivada"):
        await caso.execute(ADMIN, DatosNuevoUsuario("Dora", "dora@minsa.gob.pe", RolCodigo.GESTOR, area))


async def test_un_area_desactivada_es_no_procesable() -> None:
    caso, almacen, _ = _caso()
    almacen.areas_inactivas.add("HOSP-01")

    with pytest.raises(NoProcesable):
        await caso.execute(ADMIN, DatosNuevoUsuario("Dora", "dora@minsa.gob.pe", RolCodigo.GESTOR, "HOSP-01"))


async def test_el_establecimiento_crea_en_su_propia_area_e_ignora_el_area_pedida() -> None:
    caso, _, _ = _caso()

    creado = await caso.execute(
        ESTABLECIMIENTO, DatosNuevoUsuario("Dora", "dora@minsa.gob.pe", RolCodigo.GESTOR, "HOSP-02")
    )

    assert creado.usuario.area_codigo == "HOSP-01"


async def test_el_establecimiento_sin_area_no_puede_crear() -> None:
    caso, _, _ = _caso()
    sesion = una_sesion(roles=("ESTABLECIMIENTO",), area=None)

    with pytest.raises(SinPermiso, match="no tiene un establecimiento"):
        await caso.execute(sesion, DatosNuevoUsuario("Dora", "dora@minsa.gob.pe", RolCodigo.GESTOR))


@pytest.mark.parametrize("rol", [RolCodigo.ADMINISTRADOR, RolCodigo.OTRANS])
async def test_el_establecimiento_no_puede_asignar_roles_fuera_de_los_suyos(rol: RolCodigo) -> None:
    caso, almacen, hasher = _caso()

    with pytest.raises(SinPermiso, match="No puedes asignar ese rol"):
        await caso.execute(ESTABLECIMIENTO, DatosNuevoUsuario("Dora", "dora@minsa.gob.pe", rol))

    assert hasher.hashes == []
    assert almacen.usuarios == {}


async def test_quien_no_gestiona_usuarios_recibe_403() -> None:
    caso, _, _ = _caso()

    with pytest.raises(SinPermiso):
        await caso.execute(
            una_sesion(roles=("GESTOR",)), DatosNuevoUsuario("Dora", "d@minsa.gob.pe", RolCodigo.GESTOR, "HOSP-01")
        )


async def test_un_correo_repetido_deshace_la_creacion() -> None:
    caso, almacen, _ = _caso(UsuariosEnMemoria([un_usuario_gestionado(correo="dora@minsa.gob.pe")]))

    with pytest.raises(CorreoRepetido):
        await caso.execute(ADMIN, DatosNuevoUsuario("Dora", "dora@minsa.gob.pe", RolCodigo.GESTOR, "HOSP-01"))

    assert len(almacen.usuarios) == 1
