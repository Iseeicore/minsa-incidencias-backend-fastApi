import json
from importlib.resources import files
from typing import Any

CODIFICACION_DE_DATOS = "utf-8"


def cargar_datos(nombre: str) -> Any:  # noqa: ANN401
    texto = files("app.constants").joinpath("datos", nombre).read_text(encoding=CODIFICACION_DE_DATOS)
    return json.loads(texto)
