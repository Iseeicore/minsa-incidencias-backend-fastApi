from dataclasses import replace
from typing import TYPE_CHECKING

from app.constants.incidencias import CATEGORIA_DESDE_API, ESTADO_DESDE_API
from app.enums.categoria_api import CategoriaApi
from app.enums.categoria_filtro import CategoriaFiltro
from app.incidencias.domain.consultas import FiltrosCasos

if TYPE_CHECKING:
    from app.incidencias.domain.consultas import FiltrosConsulta
    from app.incidencias.domain.plazo import PlazosConfigurados


def filtros_de(consulta: FiltrosConsulta, plazos: PlazosConfigurados) -> FiltrosCasos:
    sin_categoria = consulta.categoria == CategoriaFiltro.SIN_CATEGORIA
    categoria = (
        CATEGORIA_DESDE_API[CategoriaApi(consulta.categoria.value)]
        if consulta.categoria is not None and not sin_categoria
        else None
    )
    return FiltrosCasos(
        estado=ESTADO_DESDE_API[consulta.estado] if consulta.estado is not None else None,
        categoria=categoria,
        sin_categoria=sin_categoria,
        texto=consulta.texto,
        establecimiento=consulta.establecimiento,
        motivo_archivo=consulta.motivo_archivo,
        desde=consulta.desde,
        hasta=consulta.hasta,
        aviso_horas=plazos.aviso_horas if consulta.por_vencer else None,
    )


def sin_estado_ni_motivo(filtros: FiltrosCasos) -> FiltrosCasos:
    return replace(filtros, estado=None, motivo_archivo=None)
