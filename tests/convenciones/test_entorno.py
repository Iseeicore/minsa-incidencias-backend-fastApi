import re
from pathlib import Path

from app.config.settings import Settings

RAIZ = Path(__file__).parents[2]
VARIABLES_DE_SETTINGS = {nombre.upper() for nombre in Settings.model_fields}


def _variables_del_ejemplo() -> set[str]:
    lineas = (RAIZ / ".env.example").read_text(encoding="utf-8").splitlines()
    return {linea.split("=", 1)[0] for linea in lineas if "=" in linea}


def _variables_del_readme() -> set[str]:
    texto = (RAIZ / "README.md").read_text(encoding="utf-8")
    return set(re.findall(r"^\| `([A-Z][A-Z0-9_]+)` \|", texto, flags=re.MULTILINE))


def test_el_ejemplo_de_entorno_lista_exactamente_las_variables_que_lee_la_configuracion() -> None:
    assert _variables_del_ejemplo() == VARIABLES_DE_SETTINGS


def test_la_tabla_del_readme_lista_exactamente_las_variables_que_lee_la_configuracion() -> None:
    assert _variables_del_readme() == VARIABLES_DE_SETTINGS
