from typing import TYPE_CHECKING

from app.archivador.domain.resultado_de_archivado import ResultadoDeArchivado
from app.constants.textos.procesos import EVENTO_ARCHIVADO_COMPLETADO, EVENTO_FALLO_EL_ARCHIVADO

if TYPE_CHECKING:
    from app.archivador.application.ports import ArchivadoRepositorio
    from app.shared.ports import RegistroDeProcesos


class ArchivarIncidencias:
    def __init__(
        self, repositorio: ArchivadoRepositorio, registro: RegistroDeProcesos, *, vigencia_dias: int, lote: int
    ) -> None:
        self._repositorio = repositorio
        self._registro = registro
        self._vigencia_dias = vigencia_dias
        self._lote = lote
        self._en_curso = False

    async def ejecutar(self) -> ResultadoDeArchivado:
        if self._en_curso:
            return ResultadoDeArchivado()
        self._en_curso = True
        try:
            abiertas = await self._repositorio.archivar_vencidas(self._lote)
            resueltas = await self._repositorio.archivar_resueltas(self._vigencia_dias, self._lote)
            return ResultadoDeArchivado(abiertas, resueltas)
        finally:
            self._en_curso = False

    async def ejecutar_con_registro(self) -> None:
        try:
            resultado = await self.ejecutar()
        except Exception as error:  # noqa: BLE001
            self._registro.error(EVENTO_FALLO_EL_ARCHIVADO, error=type(error).__name__)
            return
        if resultado.hubo_cambios:
            self._registro.info(EVENTO_ARCHIVADO_COMPLETADO, abiertas=resultado.abiertas, resueltas=resultado.resueltas)
