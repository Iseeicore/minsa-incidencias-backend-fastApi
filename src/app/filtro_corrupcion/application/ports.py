from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from app.filtro_corrupcion.domain.cola_de_clasificacion import (
        AnalisisAGuardar,
        CasoPendiente,
        CategoriaAEscribir,
        FilaAlarma,
    )
    from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia


class ClasificadorTransaction(Protocol):
    async def siguiente_pendiente(
        self, abandonados: tuple[str, ...], solo_casos: tuple[str, ...] | None
    ) -> CasoPendiente | None: ...

    async def area_mencionada(self, codigo: str) -> int | None: ...

    async def buscar_coincidencias(self, incidencia_id: str, texto: str) -> list[CandidatoCoincidencia]: ...

    async def registrar_analisis(self, analisis: AnalisisAGuardar) -> None: ...

    async def actualizar_categoria(self, categoria: CategoriaAEscribir) -> None: ...


class ClasificadorUnitOfWork(Protocol):
    def begin(self, actor: str) -> AbstractAsyncContextManager[ClasificadorTransaction]: ...


class AlarmaReader(Protocol):
    async def alarma_sin_clasificar(self, minutos: int, codigos_maximos: int) -> FilaAlarma | None: ...
