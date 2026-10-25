from typing import TYPE_CHECKING, Any

from app.incidencias.domain.caso_consultado import ConteoPorVencer

if TYPE_CHECKING:
    from app.enums.estado_incidencia import EstadoIncidencia
    from app.incidencias.domain.caso_consultado import CasoConsultado, EvidenciaConsultada
    from app.incidencias.domain.consultas import FiltrosCasos, VisibilidadOperativa
    from app.incidencias.domain.cursores import PosicionDeListado, PosicionPorVencer
    from app.incidencias.domain.fila_historial import FilaHistorial
    from app.shared.permisos import ReglaDeAccion


class IncidenciasEnMemoria:
    def __init__(
        self,
        casos: list[CasoConsultado] | None = None,
        evidencias: list[EvidenciaConsultada] | None = None,
        historial: list[FilaHistorial] | None = None,
        rutas: dict[str, str] | None = None,
    ) -> None:
        self.casos = list(casos or [])
        self._evidencias = list(evidencias or [])
        self._historial = list(historial or [])
        self._rutas = dict(rutas or {})
        self.por_estado: dict[EstadoIncidencia, int] = {}
        self.acotado = 0
        self.conteo_por_vencer = ConteoPorVencer(0, 0)
        self.llamadas: list[tuple[str, tuple[Any, ...]]] = []

    async def listar(
        self,
        visible: VisibilidadOperativa,
        filtros: FiltrosCasos,
        limite: int,
        despues_de: PosicionDeListado | None,
    ) -> list[CasoConsultado]:
        self.llamadas.append(("listar", (visible, filtros, limite, despues_de)))
        return self.casos[:limite]

    async def listar_proximos_a_vencer(
        self,
        visible: VisibilidadOperativa,
        filtros: FiltrosCasos,
        limite: int,
        despues_de: PosicionPorVencer | None,
    ) -> list[CasoConsultado]:
        self.llamadas.append(("listar_proximos_a_vencer", (visible, filtros, limite, despues_de)))
        return self.casos[:limite]

    async def contar_acotado(self, visible: VisibilidadOperativa, filtros: FiltrosCasos, tope: int) -> int:
        self.llamadas.append(("contar_acotado", (visible, filtros, tope)))
        return self.acotado

    async def contar_por_estado(
        self, visible: VisibilidadOperativa, filtros: FiltrosCasos, tope: int
    ) -> dict[EstadoIncidencia, int]:
        self.llamadas.append(("contar_por_estado", (visible, filtros, tope)))
        return dict(self.por_estado)

    async def buscar_por_codigo(self, codigo: str, visible: VisibilidadOperativa) -> CasoConsultado | None:
        self.llamadas.append(("buscar_por_codigo", (codigo, visible)))
        return next((caso for caso in self.casos if caso.codigo == codigo), None)

    async def evidencias(self, incidencia_id: str) -> list[EvidenciaConsultada]:
        self.llamadas.append(("evidencias", (incidencia_id,)))
        return list(self._evidencias)

    async def ruta_de_evidencia(self, incidencia_id: str, evidencia_id: str) -> str | None:
        self.llamadas.append(("ruta_de_evidencia", (incidencia_id, evidencia_id)))
        return self._rutas.get(evidencia_id)

    async def historial(self, incidencia_id: str) -> list[FilaHistorial]:
        self.llamadas.append(("historial", (incidencia_id,)))
        return list(self._historial)

    async def contar_por_vencer(
        self, visible: VisibilidadOperativa, aviso_horas: int, pendientes: tuple[ReglaDeAccion, ...] | None
    ) -> ConteoPorVencer:
        self.llamadas.append(("contar_por_vencer", (visible, aviso_horas, pendientes)))
        return self.conteo_por_vencer

    async def listar_por_vencer(
        self,
        visible: VisibilidadOperativa,
        aviso_horas: int,
        limite: int,
        pendientes: tuple[ReglaDeAccion, ...] | None,
    ) -> list[CasoConsultado]:
        self.llamadas.append(("listar_por_vencer", (visible, aviso_horas, limite, pendientes)))
        return self.casos[:limite]
