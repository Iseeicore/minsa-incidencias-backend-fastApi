from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.enums.estado_incidencia import EstadoIncidencia
    from app.incidencias.domain.caso_consultado import CasoConsultado, ConteoPorVencer, EvidenciaConsultada
    from app.incidencias.domain.consultas import FiltrosCasos, VisibilidadOperativa
    from app.incidencias.domain.cursores import PosicionDeListado, PosicionPorVencer
    from app.incidencias.domain.fila_historial import FilaHistorial
    from app.shared.permisos import ReglaDeAccion


class IncidenciaReader(Protocol):
    async def listar(
        self,
        visible: VisibilidadOperativa,
        filtros: FiltrosCasos,
        limite: int,
        despues_de: PosicionDeListado | None,
    ) -> list[CasoConsultado]: ...

    async def listar_proximos_a_vencer(
        self,
        visible: VisibilidadOperativa,
        filtros: FiltrosCasos,
        limite: int,
        despues_de: PosicionPorVencer | None,
    ) -> list[CasoConsultado]: ...

    async def contar_acotado(self, visible: VisibilidadOperativa, filtros: FiltrosCasos, tope: int) -> int: ...

    async def contar_por_estado(
        self, visible: VisibilidadOperativa, filtros: FiltrosCasos, tope: int
    ) -> dict[EstadoIncidencia, int]: ...

    async def buscar_por_codigo(self, codigo: str, visible: VisibilidadOperativa) -> CasoConsultado | None: ...

    async def evidencias(self, incidencia_id: str) -> list[EvidenciaConsultada]: ...

    async def ruta_de_evidencia(self, incidencia_id: str, evidencia_id: str) -> str | None: ...

    async def historial(self, incidencia_id: str) -> list[FilaHistorial]: ...

    async def contar_por_vencer(
        self, visible: VisibilidadOperativa, aviso_horas: int, pendientes: tuple[ReglaDeAccion, ...] | None
    ) -> ConteoPorVencer: ...

    async def listar_por_vencer(
        self,
        visible: VisibilidadOperativa,
        aviso_horas: int,
        limite: int,
        pendientes: tuple[ReglaDeAccion, ...] | None,
    ) -> list[CasoConsultado]: ...
