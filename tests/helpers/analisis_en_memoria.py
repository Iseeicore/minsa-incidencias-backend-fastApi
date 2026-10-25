from datetime import UTC, datetime
from typing import Any

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.incidencias.domain.analisis import FilaAnalisis


def una_fila_de_analisis(**cambios: Any) -> FilaAnalisis:  # noqa: ANN401
    base: dict[str, Any] = {
        "version_reglas": "reglas-corrupcion-v1.3",
        "puntaje": 5,
        "senales": {},
        "cargo_mencionado": "jefa",
        "nombre_mencionado": None,
        "area_mencionada_codigo": None,
        "area_mencionada_nombre": None,
        "categoria_ia": CategoriaIncidencia.DENUNCIA_CORRUPCION,
        "confianza_ia": 82.0,
        "version_clasificador": "coincidencias-v1",
        "fecha_analisis": datetime(2026, 10, 24, 12, 0, 0, 789_000, tzinfo=UTC),
    }
    return FilaAnalisis(**{**base, **cambios})


class AnalisisEnMemoria:
    def __init__(self, filas: dict[str, FilaAnalisis] | None = None) -> None:
        self.filas = dict(filas or {})
        self.consultas: list[str] = []

    async def buscar(self, incidencia_id: str) -> FilaAnalisis | None:
        self.consultas.append(incidencia_id)
        return self.filas.get(incidencia_id)
