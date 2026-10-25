import pytest

from app.enums.rol_codigo import RolCodigo
from app.errors.conflicto import Conflicto
from app.errors.no_procesable import NoProcesable
from app.usuarios.application.crear_administrador import CrearAdministrador
from app.usuarios.domain.pedidos import DatosDeAdministrador
from tests.helpers.acceso_en_memoria import HasherFalso
from tests.helpers.builders import un_usuario_gestionado
from tests.helpers.usuarios_en_memoria import UsuariosEnMemoria

CLAVE = "una-clave-larga-1"


def _caso(almacen: UsuariosEnMemoria | None = None) -> tuple[CrearAdministrador, UsuariosEnMemoria, HasherFalso]:
    almacen = almacen or UsuariosEnMemoria()
    hasher = HasherFalso()
    return CrearAdministrador(almacen, hasher), almacen, hasher


async def test_crea_un_administrador_con_el_correo_normalizado_la_huella_y_sin_area() -> None:
    caso, almacen, hasher = _caso()

    await caso.execute(DatosDeAdministrador("Ana Torres", "  ANA@Minsa.GOB.pe ", CLAVE))

    [usuario] = almacen.usuarios.values()
    assert (usuario.nombre_completo, usuario.correo, usuario.rol, usuario.area_id) == (
        "Ana Torres",
        "ana@minsa.gob.pe",
        RolCodigo.ADMINISTRADOR.value,
        None,
    )
    assert almacen.huellas[usuario.id] == f"hash:{CLAVE}"
    assert hasher.hashes == [CLAVE]
    assert almacen.actores == ["sistema:crear-admin"]


async def test_puede_crear_al_administrador_dentro_de_un_area_activa() -> None:
    caso, almacen, _ = _caso()

    await caso.execute(DatosDeAdministrador("Ana Torres", "ana@minsa.gob.pe", CLAVE, "HOSP-01"))

    [usuario] = almacen.usuarios.values()
    assert (usuario.area_id, usuario.area_codigo) == (1, "HOSP-01")


async def test_un_area_inexistente_se_rechaza_con_su_codigo_y_no_crea_nada() -> None:
    caso, almacen, _ = _caso()

    with pytest.raises(NoProcesable) as error:
        await caso.execute(DatosDeAdministrador("Ana Torres", "ana@minsa.gob.pe", CLAVE, "NO-EXISTE"))

    assert error.value.message == "No existe un área activa con el código NO-EXISTE."
    assert almacen.usuarios == {}


async def test_un_correo_repetido_responde_conflicto_con_su_mensaje() -> None:
    existente = un_usuario_gestionado("11111111-1111-4111-8111-111111111111", "Ana", "ana@minsa.gob.pe", "GESTOR", 1)
    caso, almacen, _ = _caso(UsuariosEnMemoria([existente]))

    with pytest.raises(Conflicto) as error:
        await caso.execute(DatosDeAdministrador("Otra Ana", "ANA@minsa.gob.pe", CLAVE))

    assert error.value.message == "Ya existe un usuario con ese correo."
    assert len(almacen.usuarios) == 1
