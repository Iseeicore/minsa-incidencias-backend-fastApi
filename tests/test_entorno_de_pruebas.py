import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).parents[1]
CODIGO_DE_SALIDA_SIN_BASE = 2


def _correr_integracion(entorno: dict[str, str]) -> subprocess.CompletedProcess[str]:
    entorno["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "integration", "-q", "-p", "no:cacheprovider", "--no-cov"],
        cwd=RAIZ,
        env=entorno,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_sin_base_las_pruebas_de_integracion_se_detienen_con_un_solo_mensaje_claro() -> None:
    entorno = {nombre: valor for nombre, valor in os.environ.items() if nombre != "TEST_DATABASE_URL"}

    resultado = _correr_integracion(entorno)

    salida = resultado.stdout + resultado.stderr
    assert resultado.returncode == CODIGO_DE_SALIDA_SIN_BASE
    assert salida.count("TEST_DATABASE_URL no está definida") == 1
    assert "Traceback" not in salida


@pytest.mark.parametrize("plantilla", ["produccion", "bd_plantilla; DROP DATABASE x", "Bd_Desechable"])
def test_una_plantilla_que_no_es_desechable_detiene_las_pruebas_de_integracion(plantilla: str) -> None:
    entorno = dict(os.environ)
    entorno["TEST_DATABASE_URL"] = "postgresql://nadie:nada@127.0.0.1:1/postgres"
    entorno["TEST_TEMPLATE_DATABASE"] = plantilla

    resultado = _correr_integracion(entorno)

    salida = resultado.stdout + resultado.stderr
    assert resultado.returncode == CODIGO_DE_SALIDA_SIN_BASE
    assert "debe ser una base desechable" in salida
    assert "Traceback" not in salida
