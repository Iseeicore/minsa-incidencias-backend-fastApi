from dataclasses import replace

import pytest

from app.enums.rol_codigo import RolCodigo
from app.errors.autoedicion_no_permitida import AutoedicionNoPermitida
from app.errors.no_encontrado import NoEncontrado
from app.errors.no_procesable import NoProcesable
from app.errors.sin_permiso import SinPermiso
from app.shared.sesion import SesionActual
from app.usuarios.application.actualizar_usuario import ActualizarUsuario
from app.usuarios.domain.pedidos import CambiosDeUsuario
from tests.helpers.builders import un_area_de_sesion, un_usuario_gestionado, una_sesion
from tests.helpers.usuarios_en_memoria import UsuariosEnMemoria

ANA = "11111111-1111-4111-8111-111111111111"
ADMIN_ID = "99999999-9999-4999-8999-999999999999"
ADMIN = una_sesion(correo="admin@minsa.gob.pe", roles=("ADMINISTRADOR",))
ESTABLECIMIENTO = una_sesion(correo="jefe@minsa.gob.pe", roles=("ESTABLECIMIENTO",), area=un_area_de_sesion(id=1))


def _almacen() -> UsuariosEnMemoria:
    return UsuariosEnMemoria(
        [
            un_usuario_gestionado(ANA, "Ana Torres", "ana@minsa.gob.pe", "GESTOR", 1),
            un_usuario_gestionado(
                "22222222-2222-4222-8222-222222222222", "Bruno Díaz", "bruno@minsa.gob.pe", "GESTOR", 2
            ),
            un_usuario_gestionado(ADMIN_ID, "Admin", "admin@minsa.gob.pe", "ADMINISTRADOR", None),
        ]
    )


def _sesion_de(usuario_id: str) -> SesionActual:
    return replace(ADMIN, usuario_id=usuario_id)


async def test_cambiar_el_nombre_lo_guarda_y_no_cierra_sesiones() -> None:
    almacen = _almacen()

    usuario = await ActualizarUsuario(almacen).execute(ADMIN, ANA, CambiosDeUsuario(nombre_completo="Ana María"))

    assert usuario.nombre_completo == "Ana María"
    assert almacen.sesiones_cerradas == []


async def test_un_nombre_igual_al_actual_no_cambia_nada() -> None:
    almacen = _almacen()

    usuario = await ActualizarUsuario(almacen).execute(
        ADMIN, ANA, CambiosDeUsuario(nombre_completo="Ana Torres", activo=True)
    )

    assert usuario == almacen.usuarios[ANA]


async def test_cambiar_el_rol_reasigna_el_rol_y_cierra_las_sesiones() -> None:
    almacen = _almacen()

    usuario = await ActualizarUsuario(almacen).execute(
        ADMIN, ANA, CambiosDeUsuario(rol=RolCodigo.OTRANS, area="HOSP-02")
    )

    assert (usuario.rol, usuario.area_codigo) == ("OTRANS", "HOSP-02")
    assert almacen.sesiones_cerradas == [ANA]


async def test_cambiar_el_rol_a_uno_con_area_sin_tenerla_es_no_procesable() -> None:
    almacen = _almacen()

    with pytest.raises(NoProcesable, match="Indica el área"):
        await ActualizarUsuario(almacen).execute(ADMIN, ADMIN_ID, CambiosDeUsuario(rol=RolCodigo.GESTOR))


async def test_cambiar_a_administrador_quita_el_area() -> None:
    almacen = _almacen()

    usuario = await ActualizarUsuario(almacen).execute(ADMIN, ANA, CambiosDeUsuario(rol=RolCodigo.ADMINISTRADOR))

    assert (usuario.rol, usuario.area_id) == ("ADMINISTRADOR", None)


async def test_cambiar_el_area_de_un_administrador_es_no_procesable() -> None:
    with pytest.raises(NoProcesable, match="no indiques el área"):
        await ActualizarUsuario(_almacen()).execute(ADMIN, ADMIN_ID, CambiosDeUsuario(area="HOSP-01"))


async def test_cambiar_a_un_area_inexistente_es_no_procesable() -> None:
    with pytest.raises(NoProcesable, match="no existe o está desactivada"):
        await ActualizarUsuario(_almacen()).execute(ADMIN, ANA, CambiosDeUsuario(area="NO-EXISTE"))


async def test_el_administrador_cambia_el_area_de_un_usuario() -> None:
    almacen = _almacen()

    usuario = await ActualizarUsuario(almacen).execute(ADMIN, ANA, CambiosDeUsuario(area="HOSP-02"))

    assert usuario.area_codigo == "HOSP-02"


async def test_desactivar_a_otro_usuario_lo_marca_inactivo() -> None:
    almacen = _almacen()

    usuario = await ActualizarUsuario(almacen).execute(ADMIN, ANA, CambiosDeUsuario(activo=False))

    assert usuario.activo is False


async def test_reactivar_a_un_usuario_inactivo_lo_marca_activo() -> None:
    almacen = UsuariosEnMemoria([un_usuario_gestionado(ANA, activo=False)])

    usuario = await ActualizarUsuario(almacen).execute(ADMIN, ANA, CambiosDeUsuario(activo=True))

    assert usuario.activo is True


async def test_nadie_puede_cambiarse_su_propio_rol_ni_desactivarse() -> None:
    almacen = _almacen()
    propia = _sesion_de(ANA)

    with pytest.raises(AutoedicionNoPermitida):
        await ActualizarUsuario(almacen).execute(propia, ANA, CambiosDeUsuario(rol=RolCodigo.OTRANS, area="HOSP-01"))
    with pytest.raises(AutoedicionNoPermitida):
        await ActualizarUsuario(almacen).execute(propia, ANA, CambiosDeUsuario(activo=False))


async def test_uno_mismo_si_puede_cambiar_su_nombre_o_repetir_su_rol() -> None:
    almacen = _almacen()
    propia = _sesion_de(ANA)

    usuario = await ActualizarUsuario(almacen).execute(
        propia, ANA, CambiosDeUsuario(nombre_completo="Ana Nueva", rol=RolCodigo.GESTOR, activo=True)
    )

    assert usuario.nombre_completo == "Ana Nueva"


async def test_un_usuario_inexistente_responde_404() -> None:
    with pytest.raises(NoEncontrado, match="El usuario solicitado no existe"):
        await ActualizarUsuario(_almacen()).execute(
            ADMIN, "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69", CambiosDeUsuario(activo=False)
        )


async def test_el_establecimiento_no_ve_a_los_usuarios_de_otra_area() -> None:
    with pytest.raises(NoEncontrado):
        await ActualizarUsuario(_almacen()).execute(
            ESTABLECIMIENTO, "22222222-2222-4222-8222-222222222222", CambiosDeUsuario(activo=False)
        )


async def test_el_establecimiento_no_puede_cambiar_el_area_de_nadie() -> None:
    with pytest.raises(SinPermiso, match="Solo el administrador cambia el área"):
        await ActualizarUsuario(_almacen()).execute(ESTABLECIMIENTO, ANA, CambiosDeUsuario(area="HOSP-02"))


async def test_el_establecimiento_puede_repetir_el_area_actual() -> None:
    usuario = await ActualizarUsuario(_almacen()).execute(
        ESTABLECIMIENTO, ANA, CambiosDeUsuario(area="HOSP-01", activo=False)
    )

    assert usuario.activo is False


async def test_el_establecimiento_no_asigna_roles_fuera_de_los_suyos() -> None:
    with pytest.raises(SinPermiso, match="No puedes asignar ese rol"):
        await ActualizarUsuario(_almacen()).execute(ESTABLECIMIENTO, ANA, CambiosDeUsuario(rol=RolCodigo.ADMINISTRADOR))


async def test_quien_no_gestiona_usuarios_recibe_403() -> None:
    with pytest.raises(SinPermiso):
        await ActualizarUsuario(_almacen()).execute(una_sesion(roles=("GESTOR",)), ANA, CambiosDeUsuario(activo=False))


async def test_un_error_a_mitad_deshace_los_cambios_ya_hechos() -> None:
    almacen = _almacen()

    with pytest.raises(NoProcesable):
        await ActualizarUsuario(almacen).execute(ADMIN, ANA, CambiosDeUsuario(rol=RolCodigo.OTRANS, area="NO-EXISTE"))

    assert almacen.usuarios[ANA].rol == "GESTOR"
    assert almacen.sesiones_cerradas == []
