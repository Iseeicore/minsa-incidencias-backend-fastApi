from typing import Any

from app.constants.datos_estaticos import cargar_datos
from app.enums.tema_norma import TemaNorma

_MAPA: list[dict[str, Any]] = cargar_datos("mapa_senal_fragmento.json")

MAPA_SENAL_FRAGMENTO = tuple(
    (
        TemaNorma(tema["tema"]),
        str(tema["descripcion"]),
        tuple[str, ...](tema["plantillas"]),
        tuple[str, ...](tema["fragmentos"]),
    )
    for tema in _MAPA
)
