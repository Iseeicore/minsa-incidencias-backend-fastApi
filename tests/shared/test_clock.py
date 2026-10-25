from datetime import UTC, datetime, timedelta

from app.shared.clock import SystemClock


def test_el_reloj_del_sistema_devuelve_la_hora_actual_en_utc() -> None:
    antes = datetime.now(UTC)

    ahora = SystemClock().now()

    assert ahora.tzinfo is not None
    assert ahora.utcoffset() == timedelta(0)
    assert antes <= ahora <= datetime.now(UTC)
