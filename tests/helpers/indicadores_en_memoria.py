from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.incidencias.domain.indicadores import FilaResumen

if TYPE_CHECKING:
    from app.incidencias.domain.consultas import Visibilidad
    from app.incidencias.domain.cubos_de_evolucion import DiaDeEvolucion
    from app.incidencias.domain.indicadores import FilaDistribucion
    from app.incidencias.domain.ipress import ConsultaDeIpress, IpressConsultada, IpressListada

GENERADO_EN = datetime(2026, 10, 24, 12, 0, 0, 456_000, tzinfo=UTC)


def un_resumen(**cambios: float | None) -> FilaResumen:
    base: dict[str, object] = {
        "generado_en": GENERADO_EN,
        "recibidos": 12,
        "recibidos_anterior": 9,
        "pendientes": 4,
        "en_gestion": 2,
        "por_vencer": 1,
        "vencidos": 1,
        "resueltos": 5,
        "resueltos_anterior": 3,
        "sin_clasificar": 2,
        "por_revisar": 3,
        "sin_tomar": 1,
        "corregidas_a_corrupcion": 1,
        "corregidas_a_corrupcion_anterior": 0,
        "segundos_promedio_de_resolucion": 66_600.0,
    }
    return FilaResumen(**{**base, **cambios})  # type: ignore[arg-type]


class IndicadoresEnMemoria:
    def __init__(self) -> None:
        self.fila = un_resumen()
        self.filas: list[FilaDistribucion] = []
        self.dias: list[DiaDeEvolucion] = []
        self.llamadas: list[tuple[str, tuple[object, ...]]] = []

    async def resumen(self, visible: Visibilidad, dias: int, aviso_horas: int) -> FilaResumen:
        self.llamadas.append(("resumen", (visible, dias, aviso_horas)))
        return self.fila

    async def distribucion(self, visible: Visibilidad) -> list[FilaDistribucion]:
        self.llamadas.append(("distribucion", (visible,)))
        return list(self.filas)

    async def evolucion_diaria(self, visible: Visibilidad, dias: int) -> list[DiaDeEvolucion]:
        self.llamadas.append(("evolucion_diaria", (visible, dias)))
        return list(self.dias)


class IpressEnMemoria:
    def __init__(
        self, encontradas: dict[str, IpressConsultada] | None = None, listadas: list[IpressListada] | None = None
    ) -> None:
        self.encontradas = dict(encontradas or {})
        self.listadas = list(listadas or [])
        self.consultas: list[tuple[ConsultaDeIpress, int]] = []

    async def buscar(self, renipress: str) -> IpressConsultada | None:
        return self.encontradas.get(renipress)

    async def listar(self, consulta: ConsultaDeIpress, limite: int) -> list[IpressListada]:
        self.consultas.append((consulta, limite))
        return self.listadas[:limite]
