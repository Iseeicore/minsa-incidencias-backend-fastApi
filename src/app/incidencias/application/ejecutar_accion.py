import asyncio
from typing import TYPE_CHECKING

from app.constants.textos.incidencias import (
    MENSAJE_ACCION_NO_PERMITIDA,
    MENSAJE_ACCION_REALIZADA,
    MENSAJE_CASO_NO_ENCONTRADO,
)
from app.errors.no_encontrado import NoEncontrado
from app.errors.sin_permiso import SinPermiso
from app.incidencias.application.armar_caso import detallar
from app.incidencias.application.visibilidad import visibilidad_de
from app.incidencias.domain.resultado_de_accion import ResultadoDeAccion
from app.shared.acciones_permitidas import CasoParaAcciones, acciones_permitidas
from app.shared.actor import actor_usuario_interno

if TYPE_CHECKING:
    from app.incidencias.application.acciones import Accion
    from app.incidencias.application.ports import IncidenciaReader, IncidenciaUnitOfWork
    from app.incidencias.domain.plazo import PlazosConfigurados
    from app.incidencias.domain.resultado_de_accion import CasoEnviadoAOtrans
    from app.shared.sesion import SesionActual


class EjecutarAccion:
    def __init__(self, unidad: IncidenciaUnitOfWork, casos: IncidenciaReader, plazos: PlazosConfigurados) -> None:
        self._unidad = unidad
        self._casos = casos
        self._plazos = plazos

    async def execute(
        self, sesion: SesionActual, codigo: str, accion: Accion
    ) -> ResultadoDeAccion | CasoEnviadoAOtrans:
        visible = visibilidad_de(sesion)
        async with self._unidad.begin(actor_usuario_interno(sesion.correo)) as tx:
            caso = await tx.buscar_bloqueando(codigo, visible)
            if caso is None:
                raise NoEncontrado(MENSAJE_CASO_NO_ENCONTRADO)
            permitidas = acciones_permitidas(sesion.roles, CasoParaAcciones(caso.estado, caso.categoria, caso.revisada))
            if accion.tipo not in permitidas:
                raise SinPermiso(MENSAJE_ACCION_NO_PERMITIDA[accion.tipo])
            await accion.aplicar(tx, sesion, caso)
        actualizado = await self._casos.buscar_por_codigo(codigo, visible)
        if actualizado is None:
            return accion.sin_vista(codigo)
        evidencias, historial = await asyncio.gather(
            self._casos.evidencias(actualizado.id), self._casos.historial(actualizado.id)
        )
        detalle = detallar(actualizado, sesion, self._plazos, evidencias, historial)
        return ResultadoDeAccion(MENSAJE_ACCION_REALIZADA[accion.tipo], detalle)
