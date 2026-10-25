from dataclasses import replace

import pytest

from app.acceso.application.resolver_sesion import ResolverSesion
from app.acceso.domain.sesion_vigente import SesionVigente
from app.errors.database_unavailable import DatabaseUnavailable
from app.shared.sesion import VigenciaDeSesion
from tests.helpers.acceso_en_memoria import SesionesDeAccesoEnMemoria
from tests.helpers.builders import un_area_de_sesion, una_sesion_vigente
from tests.helpers.eventos_en_memoria import SeguimientoEnMemoria

MINUTOS = 30


class _TocaEInvalida(SesionesDeAccesoEnMemoria):
    def __init__(self, vigentes: dict[str, SesionVigente], seguimiento: SeguimientoEnMemoria) -> None:
        super().__init__(vigentes)
        self._seguimiento = seguimiento

    async def tocar_actividad(self, actor: str, sesion_id: str, minutos_inactividad: int) -> VigenciaDeSesion | None:
        self._seguimiento.control.activo = False
        return await super().tocar_actividad(actor, sesion_id, minutos_inactividad)


class _Rota(SesionesDeAccesoEnMemoria):
    async def buscar_vigente(
        self, sesion_id: str, minutos_inactividad: int, segundos_para_tocar: int
    ) -> SesionVigente | None:
        del sesion_id, minutos_inactividad, segundos_para_tocar
        raise DatabaseUnavailable


def _caso(sesiones: SesionesDeAccesoEnMemoria, seguimiento: SeguimientoEnMemoria) -> ResolverSesion:
    return ResolverSesion(sesiones, MINUTOS, seguimiento)


async def test_una_sesion_resuelta_lleva_su_control_y_se_avisa_al_seguimiento_con_lo_que_necesita() -> None:
    vigente = replace(una_sesion_vigente(), area=un_area_de_sesion(id=7))
    seguimiento = SeguimientoEnMemoria()

    sesion = await _caso(SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente}), seguimiento).resolve(
        vigente.sesion_id
    )

    assert sesion is not None
    assert sesion.control_eventos is seguimiento.control
    assert seguimiento.verificaciones == [vigente.sesion_id]
    [en_vivo] = seguimiento.actualizadas
    assert (en_vivo.sesion_id, en_vivo.usuario_id, en_vivo.roles, en_vivo.area_id) == (
        vigente.sesion_id,
        vigente.usuario_id,
        vigente.roles,
        7,
    )
    assert (en_vivo.vigencia, en_vivo.control) == (sesion.vigencia, seguimiento.control)
    assert seguimiento.control.identificados == [vigente.usuario_id]
    assert seguimiento.control.vigente() is True
    assert seguimiento.sesiones_invalidadas == []


async def test_una_sesion_sin_area_se_avisa_con_area_nula() -> None:
    vigente = una_sesion_vigente()
    seguimiento = SeguimientoEnMemoria()

    await _caso(SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente}), seguimiento).resolve(vigente.sesion_id)

    assert seguimiento.actualizadas[0].area_id is None


async def test_una_sesion_desconocida_invalida_a_sus_flujos_y_libera_el_control() -> None:
    seguimiento = SeguimientoEnMemoria()

    resultado = await _caso(SesionesDeAccesoEnMemoria(), seguimiento).resolve("desconocida")

    assert resultado is None
    assert seguimiento.sesiones_invalidadas == ["desconocida"]
    assert seguimiento.control.vigente() is False
    assert seguimiento.actualizadas == []


async def test_una_sesion_que_ya_no_se_puede_tocar_invalida_a_sus_flujos() -> None:
    vigente = una_sesion_vigente(debe_tocar=True)
    sesiones = SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente})
    sesiones.vigencia_al_tocar = None
    seguimiento = SeguimientoEnMemoria()

    resultado = await _caso(sesiones, seguimiento).resolve(vigente.sesion_id)

    assert resultado is None
    assert seguimiento.sesiones_invalidadas == [vigente.sesion_id]
    assert seguimiento.control.vigente() is False


async def test_si_la_identidad_no_coincide_con_la_verificacion_no_hay_sesion() -> None:
    vigente = una_sesion_vigente()
    seguimiento = SeguimientoEnMemoria()
    seguimiento.control.activo = False

    resultado = await _caso(SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente}), seguimiento).resolve(
        vigente.sesion_id
    )

    assert resultado is None
    assert seguimiento.actualizadas == []
    assert seguimiento.sesiones_invalidadas == []


async def test_si_la_verificacion_se_invalida_mientras_se_toca_la_actividad_no_hay_sesion() -> None:
    vigente = una_sesion_vigente(debe_tocar=True)
    seguimiento = SeguimientoEnMemoria()
    sesiones = _TocaEInvalida({vigente.sesion_id: vigente}, seguimiento)
    sesiones.vigencia_al_tocar = vigente.vigencia

    resultado = await _caso(sesiones, seguimiento).resolve(vigente.sesion_id)

    assert resultado is None
    assert seguimiento.actualizadas == []


async def test_si_la_consulta_falla_se_libera_el_control_y_el_error_sigue_su_camino() -> None:
    seguimiento = SeguimientoEnMemoria()

    with pytest.raises(DatabaseUnavailable):
        await _caso(_Rota(), seguimiento).resolve("cualquiera")

    assert seguimiento.control.vigente() is False
