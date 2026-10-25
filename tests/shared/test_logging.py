import json

import pytest
import structlog

from app.shared.logging import configure_logging


def test_los_logs_salen_como_json_con_nivel_y_fecha(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("info")

    structlog.get_logger().info("plazos_listados", total=4)

    registro = json.loads(capsys.readouterr().out)
    assert registro["event"] == "plazos_listados"
    assert registro["total"] == 4
    assert registro["level"] == "info"
    assert registro["timestamp"].endswith("Z")


def test_un_nivel_superior_descarta_los_registros_de_menor_nivel(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("error")

    structlog.get_logger().info("ignorado")

    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("nivel", "metodo", "se_emite"),
    [
        ("warn", "info", False),
        ("warn", "warning", True),
        ("fatal", "error", False),
        ("fatal", "critical", True),
        ("trace", "debug", True),
        ("silent", "critical", False),
    ],
)
def test_los_niveles_del_contrato_filtran_como_se_espera(
    capsys: pytest.CaptureFixture[str],
    nivel: str,
    metodo: str,
    se_emite: bool,  # noqa: FBT001
) -> None:
    configure_logging(nivel)

    getattr(structlog.get_logger(), metodo)("evento")

    assert bool(capsys.readouterr().out) is se_emite
