from typing import Protocol


class ArchivadoRepositorio(Protocol):
    async def archivar_vencidas(self, lote: int) -> int: ...

    async def archivar_resueltas(self, dias: int, lote: int) -> int: ...
