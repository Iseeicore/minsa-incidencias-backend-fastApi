import pytest

from app.acceso.application.iniciar_sesion import IniciarSesion, normalizar_correo
from app.acceso.domain.usuario_interno import UsuarioInterno
from app.constants.sesion import FAKE_PASSWORD
from app.errors.credenciales_invalidas import CredencialesInvalidas
from tests.helpers.acceso_en_memoria import HasherFalso, SesionesDeAccesoEnMemoria, UsuariosDeAccesoEnMemoria
from tests.helpers.builders import un_usuario_interno

HORAS = 8


def _caso(
    usuarios: list[UsuarioInterno] | None = None,
) -> tuple[IniciarSesion, UsuariosDeAccesoEnMemoria, SesionesDeAccesoEnMemoria, HasherFalso]:
    almacen = UsuariosDeAccesoEnMemoria(usuarios if usuarios is not None else [un_usuario_interno()])
    sesiones = SesionesDeAccesoEnMemoria()
    hasher = HasherFalso()
    return IniciarSesion(almacen, sesiones, hasher, HORAS), almacen, sesiones, hasher


def test_el_correo_se_normaliza_con_recorte_y_minusculas() -> None:
    assert normalizar_correo("  ANA@Minsa.GOB.pe ") == "ana@minsa.gob.pe"


async def test_con_credenciales_validas_crea_la_sesion_con_el_actor_del_usuario() -> None:
    caso, almacen, sesiones, _ = _caso()

    sesion_id = await caso.execute("  GESTOR@minsa.gob.pe ", "clave-correcta")

    assert sesion_id
    assert almacen.consultas == ["gestor@minsa.gob.pe"]
    assert sesiones.creadas == [("usuario:gestor@minsa.gob.pe", un_usuario_interno().id, HORAS)]


async def test_una_clave_incorrecta_se_rechaza_sin_crear_sesion() -> None:
    caso, _, sesiones, _ = _caso()

    with pytest.raises(CredencialesInvalidas):
        await caso.execute("gestor@minsa.gob.pe", "otra")

    assert sesiones.creadas == []


async def test_un_usuario_inactivo_se_rechaza_aunque_la_clave_sea_correcta() -> None:
    caso, _, sesiones, _ = _caso([un_usuario_interno(activo=False)])

    with pytest.raises(CredencialesInvalidas):
        await caso.execute("gestor@minsa.gob.pe", "clave-correcta")

    assert sesiones.creadas == []


async def test_un_correo_desconocido_verifica_contra_una_huella_falsa_para_igualar_tiempos() -> None:
    caso, _, sesiones, hasher = _caso([])

    with pytest.raises(CredencialesInvalidas):
        await caso.execute("nadie@minsa.gob.pe", "clave")

    assert hasher.hashes == [FAKE_PASSWORD]
    assert hasher.verificaciones == [(f"hash:{FAKE_PASSWORD}", "clave")]
    assert sesiones.creadas == []


async def test_la_huella_falsa_se_calcula_una_sola_vez() -> None:
    caso, _, _, hasher = _caso([])

    for _ in range(3):
        with pytest.raises(CredencialesInvalidas):
            await caso.execute("nadie@minsa.gob.pe", "clave")

    assert hasher.hashes == [FAKE_PASSWORD]
    assert len(hasher.verificaciones) == 3
