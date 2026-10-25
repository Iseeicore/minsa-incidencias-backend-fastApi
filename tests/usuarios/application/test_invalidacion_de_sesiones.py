import pytest

from app.enums.rol_codigo import RolCodigo
from app.errors.no_encontrado import NoEncontrado
from app.usuarios.application.actualizar_usuario import ActualizarUsuario
from app.usuarios.application.restablecer_clave import RestablecerClave
from app.usuarios.domain.pedidos import CambiosDeUsuario
from tests.helpers.acceso_en_memoria import HasherFalso
from tests.helpers.builders import un_usuario_gestionado, una_sesion
from tests.helpers.eventos_en_memoria import SeguimientoEnMemoria
from tests.helpers.usuarios_en_memoria import UsuariosEnMemoria

ANA = "11111111-1111-4111-8111-111111111111"
ADMIN = una_sesion(correo="admin@minsa.gob.pe", roles=("ADMINISTRADOR",))


def _almacen() -> UsuariosEnMemoria:
    return UsuariosEnMemoria([un_usuario_gestionado(ANA, "Ana Torres", "ana@minsa.gob.pe", "GESTOR", 1)])


@pytest.mark.parametrize(
    "cambios",
    [
        CambiosDeUsuario(rol=RolCodigo.OTRANS, area="HOSP-02"),
        CambiosDeUsuario(area="HOSP-02"),
        CambiosDeUsuario(activo=False),
    ],
    ids=["rol", "area", "vigencia"],
)
async def test_un_cambio_que_afecta_la_sesion_invalida_al_usuario(cambios: CambiosDeUsuario) -> None:
    seguimiento = SeguimientoEnMemoria()

    await ActualizarUsuario(_almacen(), seguimiento).execute(ADMIN, ANA, cambios)

    assert seguimiento.usuarios_invalidados == [ANA]


@pytest.mark.parametrize(
    "cambios",
    [
        CambiosDeUsuario(nombre_completo="Ana María"),
        CambiosDeUsuario(activo=True),
        CambiosDeUsuario(rol=RolCodigo.GESTOR),
    ],
    ids=["nombre", "misma-vigencia", "mismo-rol"],
)
async def test_un_cambio_que_no_toca_la_sesion_no_invalida_a_nadie(cambios: CambiosDeUsuario) -> None:
    seguimiento = SeguimientoEnMemoria()

    await ActualizarUsuario(_almacen(), seguimiento).execute(ADMIN, ANA, cambios)

    assert seguimiento.usuarios_invalidados == []


async def test_si_la_actualizacion_falla_no_se_invalida_a_nadie() -> None:
    seguimiento = SeguimientoEnMemoria()

    with pytest.raises(NoEncontrado):
        await ActualizarUsuario(_almacen(), seguimiento).execute(
            ADMIN, "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69", CambiosDeUsuario(activo=False)
        )

    assert seguimiento.usuarios_invalidados == []


async def test_restablecer_la_clave_invalida_al_usuario_pero_solo_si_se_confirmo() -> None:
    seguimiento = SeguimientoEnMemoria()
    caso = RestablecerClave(_almacen(), HasherFalso(), seguimiento)

    with pytest.raises(NoEncontrado):
        await caso.execute(ADMIN, "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69")
    assert seguimiento.usuarios_invalidados == []
    await caso.execute(ADMIN, ANA)

    assert seguimiento.usuarios_invalidados == [ANA]
