import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).parents[2]
SRC = RAIZ / "src" / "app"
ARCHIVOS_DE_PRODUCCION = sorted(SRC.rglob("*.py"))
ARCHIVOS_DE_ERRORES = sorted(a for a in ARCHIVOS_DE_PRODUCCION if a.parent.name == "errors" and a.name != "__init__.py")
ARCHIVOS_DE_ENUMS = sorted(a for a in ARCHIVOS_DE_PRODUCCION if a.parent.name == "enums" and a.name != "__init__.py")
BASES_DE_ENUM = {"Enum", "StrEnum", "IntEnum"}
FUNCIONES_DE_RE = {"compile", "match", "search", "fullmatch", "sub", "subn", "findall", "finditer", "split"}
ARCHIVOS_CON_REGEX = {"nota/domain/patrones.py": "se arma con datos del propio dominio (excepción de BA67)"}
ARCHIVOS_DE_CONSTANTES = {"constantes.py"}


def _relativo(archivo: Path) -> str:
    return archivo.relative_to(SRC).as_posix()


def _clases_de(archivo: Path) -> list[ast.ClassDef]:
    return [nodo for nodo in ast.parse(archivo.read_text(encoding="utf-8")).body if isinstance(nodo, ast.ClassDef)]


def _a_pascal(nombre_de_archivo: str) -> str:
    return "".join(parte.capitalize() for parte in nombre_de_archivo.split("_"))


def _es_numerico(nodo: ast.expr) -> bool:
    if isinstance(nodo, ast.Constant):
        return isinstance(nodo.value, int | float) and not isinstance(nodo.value, bool)
    if isinstance(nodo, ast.BinOp):
        return _es_numerico(nodo.left) and _es_numerico(nodo.right)
    return False


def test_las_guardianas_recorren_archivos_reales() -> None:
    assert ARCHIVOS_DE_ERRORES
    assert ARCHIVOS_DE_ENUMS
    assert ARCHIVOS_DE_PRODUCCION


@pytest.mark.parametrize("archivo", ARCHIVOS_DE_ERRORES, ids=_relativo)
def test_cada_archivo_de_errores_define_una_sola_clase_con_el_nombre_del_archivo(archivo: Path) -> None:
    assert [clase.name for clase in _clases_de(archivo)] == [_a_pascal(archivo.stem)]


@pytest.mark.parametrize("archivo", ARCHIVOS_DE_ENUMS, ids=_relativo)
def test_cada_archivo_de_enums_define_un_solo_enum_con_el_nombre_del_archivo(archivo: Path) -> None:
    clases = _clases_de(archivo)

    assert [clase.name for clase in clases] == [_a_pascal(archivo.stem)]
    assert {base.id for base in clases[0].bases if isinstance(base, ast.Name)} & BASES_DE_ENUM


@pytest.mark.parametrize("archivo", ARCHIVOS_DE_PRODUCCION, ids=_relativo)
def test_las_expresiones_regulares_viven_solo_en_los_archivos_permitidos(archivo: Path) -> None:
    if _relativo(archivo) in ARCHIVOS_CON_REGEX:
        return
    usos = [
        nodo.lineno
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8")))
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and isinstance(nodo.func.value, ast.Name)
        and nodo.func.value.id == "re"
        and nodo.func.attr in FUNCIONES_DE_RE
    ]

    assert usos == []


@pytest.mark.parametrize("archivo", ARCHIVOS_DE_PRODUCCION, ids=_relativo)
def test_los_numeros_de_regla_viven_en_las_carpetas_de_constantes(archivo: Path) -> None:
    if "constants" in archivo.relative_to(SRC).parts or archivo.name in ARCHIVOS_DE_CONSTANTES:
        return
    asignaciones = [
        nodo.lineno
        for nodo in ast.parse(archivo.read_text(encoding="utf-8")).body
        if isinstance(nodo, ast.Assign | ast.AnnAssign)
        and nodo.value is not None
        and _es_numerico(nodo.value)
        and any(isinstance(destino, ast.Name) and destino.id.isupper() for destino in _destinos_de(nodo))
    ]

    assert asignaciones == []


def _destinos_de(nodo: ast.Assign | ast.AnnAssign) -> list[ast.expr]:
    return nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
