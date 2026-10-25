import asyncio
from typing import TYPE_CHECKING

from app.constants.indicadores import DIAS_DEL_PERIODO, DIAS_POR_CUBO_DE_EVOLUCION
from app.incidencias.application.armar_indicadores import (
    alcance_de,
    cantidades_por_categoria,
    cantidades_por_estado,
    horas_promedio,
    sumar_por_categoria,
    sumar_por_estado,
    tarjeta_de,
)
from app.incidencias.application.visibilidad import visibilidad_de
from app.incidencias.domain.cubos_de_evolucion import agrupar_en_cubos
from app.incidencias.domain.indicadores import Indicadores
from app.incidencias.domain.tiempo import a_iso
from app.shared.permisos import tarjetas_de_roles

if TYPE_CHECKING:
    from app.enums.periodo_indicadores import PeriodoIndicadores
    from app.incidencias.application.ports import IndicadoresReader
    from app.incidencias.domain.indicadores import ConsultaDeIndicadores
    from app.incidencias.domain.plazo import PlazosConfigurados
    from app.shared.sesion import SesionActual


class ObtenerIndicadores:
    def __init__(self, indicadores: IndicadoresReader, plazos: PlazosConfigurados) -> None:
        self._indicadores = indicadores
        self._plazos = plazos

    async def execute(
        self, sesion: SesionActual, periodo: PeriodoIndicadores, consulta: ConsultaDeIndicadores | None = None
    ) -> Indicadores:
        visible = consulta.visible if consulta is not None else visibilidad_de(sesion)
        alcance = consulta.alcance if consulta is not None else alcance_de(sesion)
        dias = DIAS_DEL_PERIODO[periodo]
        resumen, distribucion, por_dia = await asyncio.gather(
            self._indicadores.resumen(visible, dias, self._plazos.aviso_horas),
            self._indicadores.distribucion(visible),
            self._indicadores.evolucion_diaria(visible, dias),
        )
        por_categoria = cantidades_por_categoria(
            sumar_por_categoria(distribucion), con_sin_categoria=visible.ver_sin_categoria
        )
        return Indicadores(
            periodo=periodo,
            generado_en=a_iso(resumen.generado_en),
            alcance=alcance,
            tarjetas=tuple(tarjeta_de(codigo, resumen) for codigo in tarjetas_de_roles(sesion.roles)),
            por_categoria=tuple(fila for fila in por_categoria if fila.cantidad > 0),
            por_estado=cantidades_por_estado(sumar_por_estado(distribucion)),
            evolucion=tuple(agrupar_en_cubos(por_dia, DIAS_POR_CUBO_DE_EVOLUCION[periodo])),
            tiempo_promedio_horas=horas_promedio(resumen.segundos_promedio_de_resolucion),
        )
