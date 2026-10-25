from typing import TYPE_CHECKING

from app.incidencias.domain.derivaciones import ConteosDeDerivaciones

if TYPE_CHECKING:
    from app.incidencias.domain.derivaciones import ConsultaDeDerivaciones, DerivacionConsultada, FiltrosDeDerivaciones


class DerivacionesEnMemoria:
    def __init__(self, derivaciones: list[DerivacionConsultada] | None = None) -> None:
        self.derivaciones = list(derivaciones or [])
        self.conteos = ConteosDeDerivaciones(0, 0, 0, 0, 0)
        self.consultas: list[tuple[ConsultaDeDerivaciones, int]] = []
        self.filtros_contados: list[FiltrosDeDerivaciones] = []

    async def listar(self, consulta: ConsultaDeDerivaciones, limite: int) -> list[DerivacionConsultada]:
        self.consultas.append((consulta, limite))
        return self.derivaciones[:limite]

    async def contar(self, filtros: FiltrosDeDerivaciones) -> ConteosDeDerivaciones:
        self.filtros_contados.append(filtros)
        return self.conteos

    async def buscar_por_codigo(self, codigo: str) -> DerivacionConsultada | None:
        return next((derivacion for derivacion in self.derivaciones if derivacion.codigo_caso == codigo), None)
