from dataclasses import replace
from typing import TYPE_CHECKING

from app.constants.textos.consulta_ipress import MENSAJE_ESTABLECIMIENTO_NO_DISPONIBLE
from app.enums.alcance_indicadores import AlcanceIndicadores
from app.enums.tipo_area import TipoArea
from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.armar_indicadores import resumir_ipress
from app.incidencias.domain.consultas import VisibilidadDeIpress
from app.incidencias.domain.indicadores import AlcanceDeIndicadores, AreaDeAlcance, ConsultaDeIndicadores

if TYPE_CHECKING:
    from app.enums.periodo_indicadores import PeriodoIndicadores
    from app.incidencias.application.consultar_incidencia import ConsultarIncidencia
    from app.incidencias.application.contar_incidencias import ContarIncidencias
    from app.incidencias.application.contenido_de_evidencia import ContenidoDeEvidencia
    from app.incidencias.application.listar_incidencias import ListarIncidencias
    from app.incidencias.application.obtener_indicadores import ObtenerIndicadores
    from app.incidencias.application.ports import IndicadoresReader, IpressFinder
    from app.incidencias.domain.casos import CasoDetalle, CasoResumen, ConteosDeCasos
    from app.incidencias.domain.consultas import ConsultaListado, FiltrosConsulta
    from app.incidencias.domain.imagen_de_evidencia import ImagenDeEvidencia
    from app.incidencias.domain.indicadores import Indicadores, ResumenDeIpress
    from app.incidencias.domain.ipress import IpressConsultada
    from app.shared.pagination import Pagina
    from app.shared.sesion import SesionActual


async def ipress_de(ipress: IpressFinder, renipress: str) -> IpressConsultada:
    encontrada = await ipress.buscar(renipress)
    if encontrada is None:
        raise NoEncontrado(MENSAJE_ESTABLECIMIENTO_NO_DISPONIBLE)
    return encontrada


def visible_en(ipress: IpressConsultada) -> VisibilidadDeIpress:
    return VisibilidadDeIpress(establecimiento_id=ipress.establecimiento_id)


class ObtenerResumenDeIpress:
    def __init__(self, ipress: IpressFinder, indicadores: IndicadoresReader) -> None:
        self._ipress = ipress
        self._indicadores = indicadores

    async def execute(self, renipress: str) -> ResumenDeIpress:
        encontrada = await ipress_de(self._ipress, renipress)
        return resumir_ipress(await self._indicadores.distribucion(visible_en(encontrada)))


class ObtenerIndicadoresDeIpress:
    def __init__(self, ipress: IpressFinder, indicadores: ObtenerIndicadores) -> None:
        self._ipress = ipress
        self._indicadores = indicadores

    async def execute(self, sesion: SesionActual, renipress: str, periodo: PeriodoIndicadores) -> Indicadores:
        encontrada = await ipress_de(self._ipress, renipress)
        area = AreaDeAlcance(encontrada.codigo, encontrada.nombre, TipoArea.ESTABLECIMIENTO)
        consulta = ConsultaDeIndicadores(visible_en(encontrada), AlcanceDeIndicadores(AlcanceIndicadores.AREA, area))
        return await self._indicadores.execute(sesion, periodo, consulta)


class ListarIncidenciasDeIpress:
    def __init__(self, ipress: IpressFinder, casos: ListarIncidencias) -> None:
        self._ipress = ipress
        self._casos = casos

    async def execute(self, sesion: SesionActual, renipress: str, consulta: ConsultaListado) -> Pagina[CasoResumen]:
        encontrada = await ipress_de(self._ipress, renipress)
        sin_establecimiento = replace(consulta, filtros=replace(consulta.filtros, establecimiento=None))
        return await self._casos.execute(sesion, sin_establecimiento, visible_en(encontrada))


class ContarIncidenciasDeIpress:
    def __init__(self, ipress: IpressFinder, casos: ContarIncidencias) -> None:
        self._ipress = ipress
        self._casos = casos

    async def execute(self, sesion: SesionActual, renipress: str, filtros: FiltrosConsulta) -> ConteosDeCasos:
        encontrada = await ipress_de(self._ipress, renipress)
        return await self._casos.execute(sesion, replace(filtros, establecimiento=None), visible_en(encontrada))


class ConsultarIncidenciaDeIpress:
    def __init__(self, ipress: IpressFinder, casos: ConsultarIncidencia) -> None:
        self._ipress = ipress
        self._casos = casos

    async def execute(self, sesion: SesionActual, renipress: str, codigo: str) -> CasoDetalle:
        encontrada = await ipress_de(self._ipress, renipress)
        return await self._casos.execute(sesion, codigo, visible_en(encontrada))


class ContenidoDeEvidenciaDeIpress:
    def __init__(self, ipress: IpressFinder, contenido: ContenidoDeEvidencia) -> None:
        self._ipress = ipress
        self._contenido = contenido

    async def execute(self, sesion: SesionActual, renipress: str, codigo: str, evidencia_id: str) -> ImagenDeEvidencia:
        encontrada = await ipress_de(self._ipress, renipress)
        return await self._contenido.execute(sesion, codigo, evidencia_id, visible_en(encontrada))
