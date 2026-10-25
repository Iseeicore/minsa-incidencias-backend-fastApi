from datetime import UTC, datetime, timedelta

import pytest

from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.plazo_estado import PlazoEstado
from app.enums.plazo_tipo import PlazoTipo
from app.incidencias.domain.plazo import SIN_PLAZO, PlazosConfigurados, calcular_plazo

AHORA = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)


@pytest.mark.parametrize(
    ("horas", "estado"),
    [
        (500, PlazoEstado.EN_PLAZO),
        (49, PlazoEstado.EN_PLAZO),
        (48, PlazoEstado.POR_VENCER),
        (1, PlazoEstado.POR_VENCER),
    ],
)
def test_un_caso_abierto_con_vencimiento_futuro_se_clasifica_por_las_horas_que_le_quedan(
    horas: int, estado: PlazoEstado
) -> None:
    vence = AHORA + timedelta(hours=horas, minutes=30)

    plazo = calcular_plazo(EstadoIncidencia.CLASIFICADO, vence, None, AHORA, PLAZOS)

    assert (plazo.tipo, plazo.estado, plazo.horas_restantes) == (PlazoTipo.ATENCION, estado, horas)
    assert plazo.vence_en is not None


def test_un_caso_abierto_vencido_queda_vencido_con_horas_negativas() -> None:
    plazo = calcular_plazo(EstadoIncidencia.EN_GESTION, AHORA - timedelta(hours=5), None, AHORA, PLAZOS)

    assert (plazo.estado, plazo.horas_restantes) == (PlazoEstado.VENCIDO, -5)


def test_vencer_justo_ahora_ya_es_vencido() -> None:
    assert calcular_plazo(EstadoIncidencia.DERIVADO, AHORA, None, AHORA, PLAZOS).estado is PlazoEstado.VENCIDO


@pytest.mark.parametrize("estado", [EstadoIncidencia.REGISTRADO, EstadoIncidencia.CLASIFICADO])
def test_un_caso_abierto_sin_vencimiento_no_tiene_plazo(estado: EstadoIncidencia) -> None:
    assert calcular_plazo(estado, None, None, AHORA, PLAZOS) == SIN_PLAZO


def test_un_caso_resuelto_tiene_vigencia_desde_su_resolucion() -> None:
    plazo = calcular_plazo(EstadoIncidencia.RESUELTO, None, AHORA - timedelta(days=10), AHORA, PLAZOS)

    assert (plazo.tipo, plazo.estado, plazo.horas_restantes) == (PlazoTipo.VIGENCIA, PlazoEstado.EN_PLAZO, 20 * 24)
    assert plazo.vence_en == "2026-11-13T12:00:00.000Z"


def test_un_caso_resuelto_con_la_vigencia_cumplida_queda_vencido() -> None:
    plazo = calcular_plazo(EstadoIncidencia.RESUELTO, None, AHORA - timedelta(days=30), AHORA, PLAZOS)

    assert plazo.estado is PlazoEstado.VENCIDO


def test_un_caso_resuelto_sin_fecha_de_resolucion_no_tiene_plazo() -> None:
    assert calcular_plazo(EstadoIncidencia.RESUELTO, None, None, AHORA, PLAZOS) == SIN_PLAZO


def test_un_caso_archivado_no_tiene_plazo() -> None:
    assert calcular_plazo(EstadoIncidencia.ARCHIVADO, AHORA, AHORA, AHORA, PLAZOS) == SIN_PLAZO
