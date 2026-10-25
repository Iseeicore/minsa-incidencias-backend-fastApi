from app.acceso.application.cerrar_sesion import CerrarSesion
from tests.helpers.acceso_en_memoria import SesionesDeAccesoEnMemoria
from tests.helpers.builders import una_sesion, una_sesion_vigente
from tests.helpers.eventos_en_memoria import SeguimientoEnMemoria


async def test_cerrar_la_sesion_actual_invalida_sus_flujos() -> None:
    sesiones = SesionesDeAccesoEnMemoria()
    seguimiento = SeguimientoEnMemoria()
    sesion = una_sesion()

    await CerrarSesion(sesiones, seguimiento).de_la_sesion(sesion)

    assert sesiones.revocadas == [(f"usuario:{sesion.correo}", sesion.sesion_id)]
    assert seguimiento.sesiones_invalidadas == [sesion.sesion_id]


async def test_cerrar_por_id_invalida_los_flujos_aunque_la_sesion_ya_no_estuviera_abierta() -> None:
    vigente = una_sesion_vigente()
    sesiones = SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente})
    seguimiento = SeguimientoEnMemoria()
    caso = CerrarSesion(sesiones, seguimiento)

    await caso.por_id(vigente.sesion_id)
    await caso.por_id("0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69")

    assert len(sesiones.revocadas) == 1
    assert seguimiento.sesiones_invalidadas == [vigente.sesion_id, "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"]
