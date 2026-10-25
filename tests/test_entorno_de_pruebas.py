import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).parents[1]
CODIGO_DE_SALIDA_SIN_BASE = 2


def test_sin_base_las_pruebas_de_integracion_se_detienen_con_un_solo_mensaje_claro() -> None:
    entorno = {nombre: valor for nombre, valor in os.environ.items() if nombre != "TEST_DATABASE_URL"}
    entorno["PYTHONIOENCODING"] = "utf-8"

    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "integration", "-q", "-p", "no:cacheprovider", "--no-cov"],
        cwd=RAIZ,
        env=entorno,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    salida = resultado.stdout + resultado.stderr
    assert resultado.returncode == CODIGO_DE_SALIDA_SIN_BASE
    assert salida.count("TEST_DATABASE_URL no está definida") == 1
    assert "Traceback" not in salida
