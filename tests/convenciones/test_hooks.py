import re
import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).parents[2]
LINEAS_DE_RUN = [
    linea.strip().removeprefix("run:").strip()
    for linea in (RAIZ / "lefthook.yml").read_text(encoding="utf-8").splitlines()
    if linea.strip().startswith("run:")
]
TAREAS_DE_POE = set(tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["poe"]["tasks"])
COMANDO_DE_POE = re.compile(r"^uv run poe (?P<tarea>[a-z-]+)$")
COMANDOS_PERMITIDOS_SIN_POE = re.compile(r"^uv run (ruff|mypy)\b")


def test_los_hooks_declaran_comandos() -> None:
    assert LINEAS_DE_RUN


@pytest.mark.parametrize("comando", LINEAS_DE_RUN)
def test_ningun_comando_de_los_hooks_lleva_comillas(comando: str) -> None:
    assert '"' not in comando
    assert "'" not in comando


@pytest.mark.parametrize("comando", LINEAS_DE_RUN)
def test_cada_comando_de_los_hooks_es_una_tarea_de_poe_o_una_herramienta_sin_argumentos_con_comillas(
    comando: str,
) -> None:
    coincidencia = COMANDO_DE_POE.match(comando)

    if coincidencia:
        assert coincidencia["tarea"] in TAREAS_DE_POE
    else:
        assert COMANDOS_PERMITIDOS_SIN_POE.match(comando)
