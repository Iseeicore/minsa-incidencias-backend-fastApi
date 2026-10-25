from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.estado_incidencia import EstadoIncidencia
    from app.enums.motivo_archivo import MotivoArchivo
    from app.enums.resultado_resolucion import ResultadoResolucion
    from app.enums.tipo_area import TipoArea
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


class IncidenciaTransaction(Protocol):
    async def buscar_bloqueando(self, codigo: str, visible: VisibilidadOperativa) -> CasoConsultado | None: ...

    async def area_receptora_por_id(self, area_id: int, tipo: TipoArea) -> int | None: ...

    async def area_receptora_por_codigo(self, codigo: str, tipo: TipoArea) -> int | None: ...

    async def confirmar(self, incidencia_id: str) -> None: ...

    async def corregir(
        self, incidencia_id: str, categoria: CategoriaIncidencia, descripcion_derivacion: str | None
    ) -> None: ...

    async def derivar(self, incidencia_id: str, area_id: int, descripcion_derivacion: str) -> None: ...

    async def cambiar_estado(self, incidencia_id: str, estado: EstadoIncidencia) -> None: ...

    async def resolver(
        self, incidencia_id: str, medidas_tomadas: str, fundamento: str, resultado: ResultadoResolucion
    ) -> None: ...

    async def archivar(self, incidencia_id: str, motivo: MotivoArchivo, detalle: str) -> None: ...

    async def reabrir(self, incidencia_id: str, motivo: str) -> None: ...


class IncidenciaUnitOfWork(Protocol):
    def begin(self, actor: str) -> AbstractAsyncContextManager[IncidenciaTransaction]: ...
