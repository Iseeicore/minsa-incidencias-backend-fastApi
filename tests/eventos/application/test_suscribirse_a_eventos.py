from datetime import UTC, datetime, timedelta

import pytest

from app.enums.rol_codigo import RolCodigo
from app.enums.tipo_area import TipoArea
from app.errors.sesion_invalida import SesionInvalida
from app.eventos.application.suscribirse_a_eventos import SuscribirseAEventos
from app.eventos.domain.centro_de_eventos import CentroDeEventos
from app.shared.sesion import AreaDeSesion, SesionActual, VigenciaDeSesion
from tests.helpers.eventos_en_memoria import INICIO, ControlDePrueba, SuscriptorFalso, TiempoManual, una_vigencia
from tests.helpers.registro_en_memoria import RegistroEnMemoria


def _centro() -> CentroDeEventos:
    return CentroDeEventos(TiempoManual(), RegistroEnMemoria())


def _sesion(
    *,
    vigencia: VigenciaDeSesion | None = None,
    control: ControlDePrueba | None = None,
    area: AreaDeSesion | None = None,
) -> SesionActual:
    return SesionActual(
        sesion_id="sesion-uno",
        usuario_id="usuario-uno",
        correo="ana@minsa.gob.pe",
        nombre_completo="Ana Prueba",
        roles=(RolCodigo.GESTOR,),
        area=area,
        vigencia=vigencia,
        control_eventos=control,
    )


def test_suscribe_con_lo_que_el_centro_necesita_de_la_sesion() -> None:
    centro = _centro()
    area = AreaDeSesion(7, "EESS-6206", "Hospital de Prueba", TipoArea.ESTABLECIMIENTO)
    suscriptor = SuscriptorFalso()

    baja = SuscribirseAEventos(centro).execute(
        _sesion(vigencia=una_vigencia(), control=ControlDePrueba(), area=area), suscriptor
    )

    assert centro.conectados == 1
    baja()
    assert centro.conectados == 0


def test_una_sesion_sin_area_se_suscribe_con_area_nula() -> None:
    centro = _centro()

    SuscribirseAEventos(centro).execute(_sesion(vigencia=una_vigencia(), control=ControlDePrueba()), SuscriptorFalso())

    assert centro.conectados == 1


@pytest.mark.parametrize(
    "caso",
    ["sin-vigencia", "sin-control", "control-liberado", "vigencia-sin-zona-horaria", "inactividad-sin-zona-horaria"],
)
def test_una_sesion_sin_vigencia_ni_control_vigente_falla_cerrada_sin_suscribir(caso: str) -> None:
    centro = _centro()
    control = ControlDePrueba()
    vigencia = una_vigencia()
    if caso == "control-liberado":
        control.liberar()
    if caso == "vigencia-sin-zona-horaria":
        vigencia = VigenciaDeSesion(datetime(2030, 1, 1), INICIO + timedelta(hours=1))  # noqa: DTZ001
    if caso == "inactividad-sin-zona-horaria":
        vigencia = VigenciaDeSesion(datetime(2030, 1, 1, tzinfo=UTC), datetime(2030, 1, 1))  # noqa: DTZ001
    sesion = _sesion(
        vigencia=None if caso == "sin-vigencia" else vigencia,
        control=None if caso == "sin-control" else control,
    )

    with pytest.raises(SesionInvalida):
        SuscribirseAEventos(centro).execute(sesion, SuscriptorFalso())

    assert centro.conectados == 0
