import asyncio
from typing import TYPE_CHECKING

from app.constants.incidencias import CONTEO_TOPE, ESTADO_API
from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.application.filtros import filtros_de, sin_estado_ni_motivo
from app.incidencias.application.visibilidad import visibilidad_o_de
from app.incidencias.domain.casos import ConteoAcotado, ConteosDeCasos

if TYPE_CHECKING:
    from app.incidencias.application.ports import IncidenciaReader
    from app.incidencias.domain.consultas import FiltrosConsulta, Visibilidad
    from app.incidencias.domain.plazo import PlazosConfigurados
    from app.shared.sesion import SesionActual


def _acotar(cantidad: int, tope: int) -> ConteoAcotado:
    return ConteoAcotado(cantidad=min(cantidad, tope), con_mas=cantidad > tope)


class ContarIncidencias:
    def __init__(self, casos: IncidenciaReader, plazos: PlazosConfigurados, tope: int = CONTEO_TOPE) -> None:
        self._casos = casos
        self._plazos = plazos
        self._tope = tope

    async def execute(
        self, sesion: SesionActual, consulta: FiltrosConsulta, visibilidad: Visibilidad | None = None
    ) -> ConteosDeCasos:
        visible = visibilidad_o_de(sesion, visibilidad)
        filtros = filtros_de(consulta, self._plazos)
        acota_pestana = filtros.estado is not None or filtros.motivo_archivo is not None
        por_estado, total = await asyncio.gather(
            self._casos.contar_por_estado(visible, sin_estado_ni_motivo(filtros), self._tope),
            self._casos.contar_acotado(visible, filtros, self._tope) if acota_pestana else _sin_conteo(),
        )
        todos = sum(por_estado.values())
        return ConteosDeCasos(
            todos=_acotar(todos, self._tope),
            total=_acotar(total if total is not None else todos, self._tope),
            por_estado={
                ESTADO_API[estado]: _acotar(por_estado.get(estado, 0), self._tope) for estado in EstadoIncidencia
            },
        )


async def _sin_conteo() -> None:
    return None
