from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResultadoDeArchivado:
    abiertas: int = 0
    resueltas: int = 0

    @property
    def hubo_cambios(self) -> bool:
        return self.abiertas > 0 or self.resueltas > 0
