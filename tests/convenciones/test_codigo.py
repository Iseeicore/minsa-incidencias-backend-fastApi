import ast
import io
import tokenize
from pathlib import Path

import pytest

RAIZ = Path(__file__).parents[2]
SRC = RAIZ / "src" / "app"
TESTS = RAIZ / "tests"
ARCHIVOS_DE_CODIGO = sorted([*SRC.rglob("*.py"), *TESTS.rglob("*.py")])
ARCHIVOS_DE_PRODUCCION = sorted(SRC.rglob("*.py"))
DIRECTIVAS_PERMITIDAS = ("# noqa", "# type:", "# pragma", "# fmt:", "#!")
MAX_LINEAS_POR_ARCHIVO = 300
CONFIG = SRC / "config"
COMPOSICION = SRC / "composition.py"
ESPEJO_SIN_PRUEBA_PROPIA = {
    "composition.py": "lo cubren las pruebas de test_composition.py y de los routers",
    "main.py": "arranque real; excluido de la cobertura por BC21",
    "wiring.py": "lo cubre tests/test_wiring.py con una base real",
    "__main__.py": "punto de entrada del contenedor; excluido de la cobertura por BC21",
    "config/settings.py": "su prueba vive en tests/config/test_settings.py",
    "catalogos/application/ports.py": "solo protocolos; mypy comprueba su cumplimiento",
    "acceso/application/ports.py": "solo protocolos; mypy comprueba su cumplimiento",
    "usuarios/application/ports.py": "solo protocolos; mypy comprueba su cumplimiento",
    "usuarios/adapters/persistence/consultas.py": "solo consultas SQL; las cubre test_repository.py",
    "shared/sesion.py": "contenedor de datos cubierto por tests/shared/test_auth_deps.py",
    "shared/ports.py": "solo protocolos; mypy comprueba su cumplimiento",
    "catalogos/adapters/http/schemas.py": "los cubren test_router.py y test_contract.py",
    "catalogos/adapters/persistence/tables.py": "las cubre test_repository.py",
    "shared/http_errors.py": "lo cubre tests/shared/test_http_errors.py",
}
CARPETAS_SIN_PRUEBA_PROPIA = {
    "constants": "solo constantes con nombre",
    "enums": "solo miembros de enum",
    "errors": "clases de error con prueba de conducta en tests/errors y en la carpeta errors de cada contexto",
}


def _relativo(archivo: Path) -> str:
    return archivo.relative_to(RAIZ).as_posix()


@pytest.mark.parametrize("archivo", ARCHIVOS_DE_CODIGO, ids=_relativo)
def test_el_codigo_no_lleva_comentarios(archivo: Path) -> None:
    texto = archivo.read_text(encoding="utf-8")
    comentarios = [
        f"{token.start[0]}: {token.string}"
        for token in tokenize.generate_tokens(io.StringIO(texto).readline)
        if token.type == tokenize.COMMENT and not token.string.startswith(DIRECTIVAS_PERMITIDAS)
    ]

    assert comentarios == []


@pytest.mark.parametrize("archivo", ARCHIVOS_DE_PRODUCCION, ids=_relativo)
def test_el_entorno_solo_se_lee_en_el_modulo_de_configuracion(archivo: Path) -> None:
    if CONFIG in archivo.parents:
        return
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    lecturas = [
        nodo.lineno
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Attribute)
        and isinstance(nodo.value, ast.Name)
        and nodo.value.id == "os"
        and nodo.attr in {"environ", "getenv"}
    ]

    assert lecturas == []


@pytest.mark.parametrize("archivo", ARCHIVOS_DE_PRODUCCION, ids=_relativo)
def test_ningun_archivo_de_produccion_pasa_del_limite_de_lineas(archivo: Path) -> None:
    assert len(archivo.read_text(encoding="utf-8").splitlines()) <= MAX_LINEAS_POR_ARCHIVO


def test_el_dominio_es_sincrono() -> None:
    asincronos = [
        f"{_relativo(archivo)}:{nodo.lineno}"
        for archivo in SRC.rglob("domain/*.py")
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8")))
        if isinstance(nodo, ast.AsyncFunctionDef | ast.Await | ast.AsyncFor | ast.AsyncWith)
    ]

    assert asincronos == []


@pytest.mark.parametrize("archivo", ARCHIVOS_DE_PRODUCCION, ids=_relativo)
def test_el_prefijo_de_version_solo_se_monta_en_la_raiz_de_composicion(archivo: Path) -> None:
    if archivo == COMPOSICION:
        return
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    literales = [
        nodo.value
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) and nodo.value.startswith(("/v1", "/v2"))
    ]

    assert literales == []


@pytest.mark.parametrize("archivo", [a for a in ARCHIVOS_DE_PRODUCCION if a.name != "__init__.py"], ids=_relativo)
def test_cada_archivo_de_produccion_tiene_su_prueba_en_el_espejo(archivo: Path) -> None:
    relativo = archivo.relative_to(SRC)
    if relativo.as_posix() in ESPEJO_SIN_PRUEBA_PROPIA or CARPETAS_SIN_PRUEBA_PROPIA.keys() & set(relativo.parts[:-1]):
        return
    prueba = TESTS / relativo.parent / f"test_{relativo.stem}.py"

    assert prueba.exists(), f"falta {_relativo(prueba)}"
