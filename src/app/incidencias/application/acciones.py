from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from app.constants.textos.incidencias import MENSAJE_ACCION_REALIZADA
from app.enums.accion_incidencia import AccionIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.domain.resultado_de_accion import CasoEnviadoAOtrans, ResultadoDeAccion

if TYPE_CHECKING:
    from app.enums.motivo_archivo import MotivoArchivo
    from app.enums.resultado_resolucion import ResultadoResolucion
    from app.incidencias.application.ports import IncidenciaTransaction
    from app.incidencias.domain.caso_consultado import CasoConsultado
    from app.shared.sesion import SesionActual


class Accion(ABC):
    tipo: ClassVar[AccionIncidencia]

    @abstractmethod
    async def aplicar(self, tx: IncidenciaTransaction, sesion: SesionActual, caso: CasoConsultado) -> None: ...

    def sin_vista(self, codigo: str) -> ResultadoDeAccion | CasoEnviadoAOtrans:  # noqa: ARG002
        return ResultadoDeAccion(MENSAJE_ACCION_REALIZADA[self.tipo], None)


@dataclass(frozen=True, slots=True)
class Confirmar(Accion):
    tipo: ClassVar[AccionIncidencia] = AccionIncidencia.CONFIRMAR

    async def aplicar(self, tx: IncidenciaTransaction, sesion: SesionActual, caso: CasoConsultado) -> None:  # noqa: ARG002
        await tx.confirmar(caso.id)


@dataclass(frozen=True, slots=True)
class Tomar(Accion):
    tipo: ClassVar[AccionIncidencia] = AccionIncidencia.TOMAR

    async def aplicar(self, tx: IncidenciaTransaction, sesion: SesionActual, caso: CasoConsultado) -> None:  # noqa: ARG002
        await tx.cambiar_estado(caso.id, EstadoIncidencia.EN_GESTION)


@dataclass(frozen=True, slots=True)
class Resolver(Accion):
    tipo: ClassVar[AccionIncidencia] = AccionIncidencia.RESOLVER
    medidas_tomadas: str
    fundamento: str
    resultado: ResultadoResolucion

    async def aplicar(self, tx: IncidenciaTransaction, sesion: SesionActual, caso: CasoConsultado) -> None:  # noqa: ARG002
        await tx.resolver(caso.id, self.medidas_tomadas, self.fundamento, self.resultado)


@dataclass(frozen=True, slots=True)
class Archivar(Accion):
    tipo: ClassVar[AccionIncidencia] = AccionIncidencia.ARCHIVAR
    motivo: MotivoArchivo
    detalle: str

    async def aplicar(self, tx: IncidenciaTransaction, sesion: SesionActual, caso: CasoConsultado) -> None:  # noqa: ARG002
        await tx.archivar(caso.id, self.motivo, self.detalle)


@dataclass(frozen=True, slots=True)
class Reabrir(Accion):
    tipo: ClassVar[AccionIncidencia] = AccionIncidencia.REABRIR
    motivo: str

    async def aplicar(self, tx: IncidenciaTransaction, sesion: SesionActual, caso: CasoConsultado) -> None:  # noqa: ARG002
        await tx.reabrir(caso.id, self.motivo)
