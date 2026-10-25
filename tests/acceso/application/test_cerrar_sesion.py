from app.acceso.application.cerrar_sesion import CerrarSesion
from tests.helpers.acceso_en_memoria import SesionesDeAccesoEnMemoria
from tests.helpers.builders import una_sesion, una_sesion_vigente


async def test_cerrar_la_sesion_actual_la_revoca_con_el_actor_de_su_dueno() -> None:
    sesiones = SesionesDeAccesoEnMemoria()
    sesion = una_sesion()

    await CerrarSesion(sesiones).de_la_sesion(sesion)

    assert sesiones.revocadas == [(f"usuario:{sesion.correo}", sesion.sesion_id)]


async def test_cerrar_por_id_revoca_una_sesion_abierta_con_el_actor_de_su_dueno() -> None:
    vigente = una_sesion_vigente()
    sesiones = SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente})

    await CerrarSesion(sesiones).por_id(vigente.sesion_id)

    assert sesiones.revocadas == [(f"usuario:{vigente.correo}", vigente.sesion_id)]


async def test_cerrar_por_id_una_sesion_que_no_esta_abierta_no_hace_nada() -> None:
    sesiones = SesionesDeAccesoEnMemoria()

    await CerrarSesion(sesiones).por_id("0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69")

    assert sesiones.revocadas == []
