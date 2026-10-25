from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from app.incidencias.domain.caso_consultado import ConteoPorVencer

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.estado_incidencia import EstadoIncidencia
    from app.enums.motivo_archivo import MotivoArchivo
    from app.enums.resultado_resolucion import ResultadoResolucion
    from app.enums.tipo_area import TipoArea
    from app.incidencias.domain.caso_consultado import CasoConsultado, EvidenciaConsultada
    from app.incidencias.domain.consultas import FiltrosCasos, Visibilidad, VisibilidadOperativa
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
        self.actores: list[str] = []
        self.areas_por_id: dict[tuple[int, TipoArea], int] = {}
        self.areas_por_codigo: dict[tuple[str, TipoArea], int] = {}
        self.ocultar_al_cerrar = False

    async def listar(
        self,
        visible: Visibilidad,
        filtros: FiltrosCasos,
        limite: int,
        despues_de: PosicionDeListado | None,
    ) -> list[CasoConsultado]:
        self.llamadas.append(("listar", (visible, filtros, limite, despues_de)))
        return self.casos[:limite]

    async def listar_proximos_a_vencer(
        self,
        visible: Visibilidad,
        filtros: FiltrosCasos,
        limite: int,
        despues_de: PosicionPorVencer | None,
    ) -> list[CasoConsultado]:
        self.llamadas.append(("listar_proximos_a_vencer", (visible, filtros, limite, despues_de)))
        return self.casos[:limite]

    async def contar_acotado(self, visible: Visibilidad, filtros: FiltrosCasos, tope: int) -> int:
        self.llamadas.append(("contar_acotado", (visible, filtros, tope)))
        return self.acotado

    async def contar_por_estado(
        self, visible: Visibilidad, filtros: FiltrosCasos, tope: int
    ) -> dict[EstadoIncidencia, int]:
        self.llamadas.append(("contar_por_estado", (visible, filtros, tope)))
        return dict(self.por_estado)

    async def buscar_por_codigo(self, codigo: str, visible: Visibilidad) -> CasoConsultado | None:
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
        self, visible: Visibilidad, aviso_horas: int, pendientes: tuple[ReglaDeAccion, ...] | None
    ) -> ConteoPorVencer:
        self.llamadas.append(("contar_por_vencer", (visible, aviso_horas, pendientes)))
        return self.conteo_por_vencer

    async def listar_por_vencer(
        self,
        visible: Visibilidad,
        aviso_horas: int,
        limite: int,
        pendientes: tuple[ReglaDeAccion, ...] | None,
    ) -> list[CasoConsultado]:
        self.llamadas.append(("listar_por_vencer", (visible, aviso_horas, limite, pendientes)))
        return self.casos[:limite]

    @asynccontextmanager
    async def begin(self, actor: str) -> AsyncIterator[IncidenciasEnMemoria]:
        self.actores.append(actor)
        yield self
        if self.ocultar_al_cerrar:
            self.casos.clear()

    async def buscar_bloqueando(self, codigo: str, visible: VisibilidadOperativa) -> CasoConsultado | None:
        self.llamadas.append(("buscar_bloqueando", (codigo, visible)))
        return next((caso for caso in self.casos if caso.codigo == codigo), None)

    async def area_receptora_por_id(self, area_id: int, tipo: TipoArea) -> int | None:
        self.llamadas.append(("area_receptora_por_id", (area_id, tipo)))
        return self.areas_por_id.get((area_id, tipo))

    async def area_receptora_por_codigo(self, codigo: str, tipo: TipoArea) -> int | None:
        self.llamadas.append(("area_receptora_por_codigo", (codigo, tipo)))
        return self.areas_por_codigo.get((codigo, tipo))

    async def confirmar(self, incidencia_id: str) -> None:
        self.llamadas.append(("confirmar", (incidencia_id,)))

    async def corregir(
        self, incidencia_id: str, categoria: CategoriaIncidencia, descripcion_derivacion: str | None
    ) -> None:
        self.llamadas.append(("corregir", (incidencia_id, categoria, descripcion_derivacion)))

    async def derivar(self, incidencia_id: str, area_id: int, descripcion_derivacion: str) -> None:
        self.llamadas.append(("derivar", (incidencia_id, area_id, descripcion_derivacion)))

    async def cambiar_estado(self, incidencia_id: str, estado: EstadoIncidencia) -> None:
        self.llamadas.append(("cambiar_estado", (incidencia_id, estado)))

    async def resolver(
        self, incidencia_id: str, medidas_tomadas: str, fundamento: str, resultado: ResultadoResolucion
    ) -> None:
        self.llamadas.append(("resolver", (incidencia_id, medidas_tomadas, fundamento, resultado)))

    async def archivar(self, incidencia_id: str, motivo: MotivoArchivo, detalle: str) -> None:
        self.llamadas.append(("archivar", (incidencia_id, motivo, detalle)))

    async def reabrir(self, incidencia_id: str, motivo: str) -> None:
        self.llamadas.append(("reabrir", (incidencia_id, motivo)))
