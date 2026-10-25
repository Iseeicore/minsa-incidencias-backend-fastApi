from typing import TYPE_CHECKING

from app.incidencias.application.armar_caso import resumir
from app.incidencias.application.filtros import filtros_de
from app.incidencias.application.visibilidad import visibilidad_o_de
from app.incidencias.domain.cursores import (
    PosicionDeListado,
    PosicionPorVencer,
    codificar_cursor,
    codificar_cursor_por_vencer,
)
from app.shared.pagination import Pagina, limite_con_extra, pagina_de

if TYPE_CHECKING:
    from app.incidencias.application.ports import IncidenciaReader
    from app.incidencias.domain.caso_consultado import CasoConsultado
    from app.incidencias.domain.casos import CasoResumen
    from app.incidencias.domain.consultas import ConsultaListado, Visibilidad
    from app.incidencias.domain.plazo import PlazosConfigurados
    from app.shared.sesion import SesionActual


def _cursor_de_listado(fila: CasoConsultado) -> str:
    return codificar_cursor(PosicionDeListado(fila.fecha_creacion, fila.id))


def _cursor_por_vencer(fila: CasoConsultado) -> str:
    return codificar_cursor_por_vencer(PosicionPorVencer(fila.vence_atencion_en or fila.fecha_creacion, fila.id))


class ListarIncidencias:
    def __init__(self, casos: IncidenciaReader, plazos: PlazosConfigurados) -> None:
        self._casos = casos
        self._plazos = plazos

    async def execute(
        self, sesion: SesionActual, consulta: ConsultaListado, visibilidad: Visibilidad | None = None
    ) -> Pagina[CasoResumen]:
        visible = visibilidad_o_de(sesion, visibilidad)
        filtros = filtros_de(consulta.filtros, self._plazos)
        pedidos = limite_con_extra(consulta.limite)
        if filtros.aviso_horas is not None:
            filas = await self._casos.listar_proximos_a_vencer(
                visible, filtros, pedidos, consulta.despues_de_por_vencer
            )
            pagina = pagina_de(filas, consulta.limite, _cursor_por_vencer)
        else:
            filas = await self._casos.listar(visible, filtros, pedidos, consulta.despues_de)
            pagina = pagina_de(filas, consulta.limite, _cursor_de_listado)
        items = [resumir(fila, sesion, self._plazos) for fila in pagina.items]
        return Pagina(items, pagina.siguiente, pagina.hay_mas)
