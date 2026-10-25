import re
import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).parents[2]
TEXTO_DE_LEFTHOOK = (RAIZ / "lefthook.yml").read_text(encoding="utf-8")
LINEAS_DE_RUN = [
    linea.strip().removeprefix("run:").strip()
    for linea in TEXTO_DE_LEFTHOOK.splitlines()
    if linea.strip().startswith("run:")
]
TAREAS_DE_POE = set(tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["poe"]["tasks"])
COMANDO_DE_POE = re.compile(r"^uv run poe (?P<tarea>[a-z-]+)$")
COMANDOS_PERMITIDOS_SIN_POE = re.compile(r"^uv run (ruff|mypy)\b")
PRIORIDAD_DEL_PRE_PUSH = re.compile(r"^    (?P<comando>[a-z]+):\n      priority: (?P<prioridad>\d+)", re.MULTILINE)


def test_los_hooks_declaran_comandos() -> None:
    assert LINEAS_DE_RUN


def test_cada_hook_se_detiene_en_el_primer_fallo_con_piped() -> None:
    assert "fail_fast" not in TEXTO_DE_LEFTHOOK
    assert TEXTO_DE_LEFTHOOK.count("piped: true") == TEXTO_DE_LEFTHOOK.count("\n  commands:")


def test_el_pre_push_corre_primero_la_comprobacion_barata_de_la_base() -> None:
    bloque = TEXTO_DE_LEFTHOOK.split("pre-push:", 1)[1]

    prioridades = {
        coincidencia["comando"]: int(coincidencia["prioridad"])
        for coincidencia in PRIORIDAD_DEL_PRE_PUSH.finditer(bloque)
    }

    assert prioridades["integracion"] < prioridades["verificar"]


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
