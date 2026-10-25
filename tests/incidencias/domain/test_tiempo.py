from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.incidencias.domain.tiempo import a_iso, a_milisegundos, horas_entre

BASE = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("minutos", "esperado"),
    [(0, 0), (59, 0), (60, 1), (119, 1), (120, 2), (24 * 60, 24), (-1, -1), (-60, -1), (-61, -2)],
)
def test_las_horas_entre_dos_instantes_se_redondean_hacia_abajo(minutos: int, esperado: int) -> None:
    assert horas_entre(BASE, BASE + timedelta(minutes=minutos)) == esperado


def test_el_instante_se_escribe_en_utc_con_milisegundos_como_toisostring() -> None:
    assert a_iso(datetime(2026, 10, 24, 12, 0, 0, 123_456, tzinfo=UTC)) == "2026-10-24T12:00:00.123Z"
    assert a_iso(datetime(2026, 10, 24, 12, 0, tzinfo=UTC)) == "2026-10-24T12:00:00.000Z"


def test_un_instante_con_otra_zona_se_convierte_a_utc() -> None:
    lima = timezone(timedelta(hours=-5))

    assert a_iso(datetime(2026, 10, 24, 7, 0, tzinfo=lima)) == "2026-10-24T12:00:00.000Z"


def test_los_microsegundos_se_truncan_a_milisegundos() -> None:
    assert a_milisegundos(datetime(2026, 10, 24, 12, 0, 0, 123_999, tzinfo=UTC)).microsecond == 123_000
    assert a_milisegundos(datetime(2026, 10, 24, 12, 0, 0, 999, tzinfo=UTC)).microsecond == 0
