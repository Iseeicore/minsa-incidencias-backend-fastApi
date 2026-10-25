import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).parents[2]
FLUJO_DE_GITHUB = RAIZ / ".github" / "workflows" / "ci.yml"
ARCHIVOS_DE_CI = [FLUJO_DE_GITHUB, RAIZ / ".gitlab-ci.yml"]
IMAGEN_CON_VERSION_EXACTA = re.compile(r"^\s*(?:image|container):\s*python:\d+\.\d+\.\d+-[a-z0-9.-]+$", re.MULTILINE)
IMAGEN_SIN_VERSION_EXACTA = re.compile(r"python:\d+(?:\.\d+)?-")
CORREDOR_FIJADO = re.compile(r"^\s*runs-on:\s*ubuntu-\d{2}\.\d{2}$", re.MULTILINE)
ACCION_CON_VERSION_MAYOR = re.compile(r"uses:\s*[\w./-]+@v\d+$", re.MULTILINE)
VERSION_DEL_CHECKOUT = re.compile(r"actions/checkout@v(?P<version>\d+)")
PRIMERA_VERSION_EN_NODE_24 = 5


def _nombre(archivo: Path) -> str:
    return archivo.relative_to(RAIZ).as_posix()


@pytest.mark.parametrize("archivo", ARCHIVOS_DE_CI, ids=_nombre)
def test_el_ci_no_usa_etiquetas_latest(archivo: Path) -> None:
    assert "latest" not in archivo.read_text(encoding="utf-8")


@pytest.mark.parametrize("archivo", ARCHIVOS_DE_CI, ids=_nombre)
def test_la_imagen_del_ci_tiene_version_exacta(archivo: Path) -> None:
    texto = archivo.read_text(encoding="utf-8")

    assert IMAGEN_CON_VERSION_EXACTA.search(texto)
    assert not IMAGEN_SIN_VERSION_EXACTA.search(texto)


def test_el_corredor_de_github_esta_fijado_a_una_version_de_ubuntu() -> None:
    assert CORREDOR_FIJADO.search(FLUJO_DE_GITHUB.read_text(encoding="utf-8"))


def test_cada_accion_de_github_declara_su_version_mayor() -> None:
    texto = FLUJO_DE_GITHUB.read_text(encoding="utf-8")
    acciones = re.findall(r"uses:\s*\S+", texto)

    assert acciones
    assert len(ACCION_CON_VERSION_MAYOR.findall(texto)) == len(acciones)


def test_el_checkout_usa_una_version_que_corre_en_node_24() -> None:
    coincidencia = VERSION_DEL_CHECKOUT.search(FLUJO_DE_GITHUB.read_text(encoding="utf-8"))

    assert coincidencia
    assert int(coincidencia["version"]) >= PRIMERA_VERSION_EN_NODE_24
