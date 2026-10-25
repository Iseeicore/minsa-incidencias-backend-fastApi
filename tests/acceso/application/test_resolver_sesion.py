from dataclasses import replace

from app.acceso.application.resolver_sesion import ResolverSesion
from app.enums.vista_codigo import VistaCodigo
from tests.helpers.acceso_en_memoria import SesionesDeAccesoEnMemoria
from tests.helpers.builders import un_area_de_sesion, una_sesion_vigente, una_vigencia

MINUTOS = 30


def _resolvedor(sesiones: SesionesDeAccesoEnMemoria) -> ResolverSesion:
    return ResolverSesion(sesiones, MINUTOS)


async def test_una_sesion_desconocida_no_se_resuelve() -> None:
    assert await _resolvedor(SesionesDeAccesoEnMemoria()).resolve("desconocida") is None


async def test_una_sesion_reciente_se_resuelve_sin_tocar_la_actividad() -> None:
    vigente = replace(una_sesion_vigente(), area=un_area_de_sesion())
    sesiones = SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente})

    sesion = await _resolvedor(sesiones).resolve(vigente.sesion_id)

    assert sesion is not None
    assert (sesion.sesion_id, sesion.usuario_id, sesion.correo, sesion.roles) == (
        vigente.sesion_id,
        vigente.usuario_id,
        vigente.correo,
        ("GESTOR",),
    )
    assert sesion.area == un_area_de_sesion()
    assert sesion.vigencia == una_vigencia()
    assert sesiones.tocadas == []


async def test_las_vistas_salen_de_los_roles_de_la_sesion() -> None:
    vigente = replace(una_sesion_vigente(), roles=("ADMINISTRADOR",))
    sesiones = SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente})

    sesion = await _resolvedor(sesiones).resolve(vigente.sesion_id)

    assert sesion is not None
    assert sesion.vistas == tuple(VistaCodigo)


async def test_una_sesion_con_actividad_vieja_la_toca_y_usa_la_vigencia_nueva() -> None:
    vigente = una_sesion_vigente(debe_tocar=True)
    sesiones = SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente})
    nueva = replace(una_vigencia(), inactiva_en=una_vigencia().inactiva_en.replace(hour=13))
    sesiones.vigencia_al_tocar = nueva

    sesion = await _resolvedor(sesiones).resolve(vigente.sesion_id)

    assert sesion is not None
    assert sesion.vigencia == nueva
    assert sesiones.tocadas == [(f"usuario:{vigente.correo}", vigente.sesion_id, MINUTOS)]


async def test_si_la_sesion_ya_no_se_puede_tocar_no_se_resuelve() -> None:
    vigente = una_sesion_vigente(debe_tocar=True)
    sesiones = SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente})
    sesiones.vigencia_al_tocar = None

    assert await _resolvedor(sesiones).resolve(vigente.sesion_id) is None
