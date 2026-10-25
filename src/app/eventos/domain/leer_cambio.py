import json
from typing import Any

from app.constants.eventos import EVENTOS_ID_MAXIMO_DE_ALCANCE
from app.errors.alcance_de_incidencia_invalido import AlcanceDeIncidenciaInvalido
from app.eventos.domain.cambio_de_incidencia import CambioDeIncidencia

CAMPOS_DEL_ALCANCE = ("areaAntes", "areaDespues", "categoriaAntes", "categoriaDespues")


def _identificador(valor: object) -> int | None:
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, int) or not 0 < valor <= EVENTOS_ID_MAXIMO_DE_ALCANCE:
        raise AlcanceDeIncidenciaInvalido
    return valor


def leer_cambio(payload: str | None) -> CambioDeIncidencia | None:
    if not payload:
        return None
    valor: Any = json.loads(payload)
    if not isinstance(valor, dict) or any(campo not in valor for campo in CAMPOS_DEL_ALCANCE):
        raise AlcanceDeIncidenciaInvalido
    area_antes, area_despues, categoria_antes, categoria_despues = (
        _identificador(valor[c]) for c in CAMPOS_DEL_ALCANCE
    )
    return CambioDeIncidencia(area_antes, area_despues, categoria_antes, categoria_despues)
