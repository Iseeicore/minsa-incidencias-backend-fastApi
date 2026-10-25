from typing import TYPE_CHECKING

from app.constants.textos.procesos import (
    EVENTO_ALARMA_SIN_CLASIFICAR,
    EVENTO_CICLO_DEL_CLASIFICADOR,
    EVENTO_FALLO_EL_CICLO_DEL_CLASIFICADOR,
)
from app.filtro_corrupcion.application.clasificar_incidencias import consultar_alarma_sin_clasificar, vaciar_cola

if TYPE_CHECKING:
    from app.filtro_corrupcion.application.clasificar_incidencias import ClasificadorIncidencias
    from app.filtro_corrupcion.application.ports import AlarmaReader
    from app.shared.ports import RegistroDeProcesos


class TrabajadorClasificador:
    def __init__(
        self, clasificador: ClasificadorIncidencias, lector: AlarmaReader, registro: RegistroDeProcesos
    ) -> None:
        self._clasificador = clasificador
        self._lector = lector
        self._registro = registro

    async def ejecutar(self) -> None:
        resumen = await vaciar_cola(self._clasificador)
        if resumen.clasificadas > 0 or resumen.fallos > 0:
            self._registro.info(
                EVENTO_CICLO_DEL_CLASIFICADOR,
                clasificadas=resumen.clasificadas,
                fallos=resumen.fallos,
                abandonadas=resumen.abandonadas,
                a_otrans=resumen.a_otrans,
            )
        alarma = await consultar_alarma_sin_clasificar(self._lector)
        if alarma.activa:
            self._registro.warning(
                EVENTO_ALARMA_SIN_CLASIFICAR,
                atrasados=alarma.atrasados,
                minutos_del_mas_antiguo=alarma.minutos_del_mas_antiguo,
                codigos=list(alarma.codigos),
                abandonados=len(self._clasificador.abandonados),
            )

    async def ejecutar_ciclo(self) -> None:
        try:
            await self.ejecutar()
        except Exception as error:  # noqa: BLE001
            self._registro.error(EVENTO_FALLO_EL_CICLO_DEL_CLASIFICADOR, error=type(error).__name__)
