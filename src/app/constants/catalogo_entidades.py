from typing import Any

from app.constants.datos_estaticos import cargar_datos

CATALOGO_DE_ENTIDADES = tuple[dict[str, Any], ...](cargar_datos("catalogo_de_entidades.json"))
UBICACIONES_DE_ENTIDADES = tuple[dict[str, Any], ...](cargar_datos("ubicaciones_de_entidades.json"))
