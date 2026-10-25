import pytest

from app.enums.resultado_usuario_de_prueba import ResultadoUsuarioDePrueba
from app.enums.rol_codigo import RolCodigo
from app.errors.no_procesable import NoProcesable
from app.usuarios.application.crear_usuario_de_prueba import CrearUsuarioDePrueba
from app.usuarios.domain.pedidos import DatosDeUsuarioDePrueba
from tests.helpers.acceso_en_memoria import HasherFalso
from tests.helpers.builders import un_usuario_gestionado
from tests.helpers.usuarios_en_memoria import UsuariosEnMemoria

CLAVE = "una-clave-larga-1"


def _caso(almacen: UsuariosEnMemoria | None = None) -> tuple[CrearUsuarioDePrueba, UsuariosEnMemoria, HasherFalso]:
    almacen = almacen or UsuariosEnMemoria()
    hasher = HasherFalso()
    return CrearUsuarioDePrueba(almacen, hasher), almacen, hasher


def _datos(**cambios: object) -> DatosDeUsuarioDePrueba:
    base: dict[str, object] = {
        "nombre_completo": "Gestor de Prueba",
        "correo": "  GESTOR@Minsa.GOB.pe",
        "password": CLAVE,
        "rol": RolCodigo.GESTOR,
        "area": "HOSP-01",
    }
    return DatosDeUsuarioDePrueba(**{**base, **cambios})  # type: ignore[arg-type]


async def test_crea_el_usuario_con_su_rol_su_area_y_el_actor_del_script() -> None:
    caso, almacen, hasher = _caso()

    resultado = await caso.execute(_datos())

    [usuario] = almacen.usuarios.values()
    assert resultado == ResultadoUsuarioDePrueba.CREADO
    assert (usuario.correo, usuario.rol, usuario.area_codigo) == ("gestor@minsa.gob.pe", "GESTOR", "HOSP-01")
    assert almacen.huellas[usuario.id] == f"hash:{CLAVE}"
    assert almacen.actores == ["sistema:script-prueba"]
    assert hasher.hashes == [CLAVE]


async def test_un_usuario_sin_area_se_crea_sin_area() -> None:
    caso, almacen, _ = _caso()

    await caso.execute(_datos(rol=RolCodigo.ADMINISTRADOR, area=None))

    assert next(iter(almacen.usuarios.values())).area_id is None


async def test_si_el_correo_ya_existe_lo_deja_como_estaba_sin_calcular_la_huella() -> None:
    existente = un_usuario_gestionado("11111111-1111-4111-8111-111111111111", "Ana", "gestor@minsa.gob.pe", "GESTOR", 1)
    caso, almacen, hasher = _caso(UsuariosEnMemoria([existente]))

    resultado = await caso.execute(_datos())

    assert resultado == ResultadoUsuarioDePrueba.EXISTENTE
    assert hasher.hashes == []
    assert len(almacen.usuarios) == 1


async def test_si_otro_proceso_lo_crea_a_la_vez_tambien_queda_como_existente() -> None:
    existente = un_usuario_gestionado("11111111-1111-4111-8111-111111111111", "Ana", "gestor@minsa.gob.pe", "GESTOR", 1)
    almacen = UsuariosEnMemoria([existente])
    almacen.correo_existe_ciego = True
    caso, _, _ = _caso(almacen)

    assert await caso.execute(_datos()) == ResultadoUsuarioDePrueba.EXISTENTE


async def test_un_rol_desactivado_se_rechaza_con_su_nombre() -> None:
    almacen = UsuariosEnMemoria()
    almacen.roles_inactivos.add("GESTOR")
    caso, _, _ = _caso(almacen)

    with pytest.raises(NoProcesable) as error:
        await caso.execute(_datos())

    assert error.value.message == "El rol GESTOR no existe o está desactivado."


async def test_un_area_inexistente_se_rechaza_con_su_codigo() -> None:
    caso, almacen, _ = _caso()

    with pytest.raises(NoProcesable) as error:
        await caso.execute(_datos(area="NO-EXISTE"))

    assert error.value.message == "El área NO-EXISTE no existe o está desactivada."
    assert almacen.usuarios == {}
