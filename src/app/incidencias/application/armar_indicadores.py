import math
from typing import TYPE_CHECKING

from app.constants.incidencias import CATEGORIA_API, ESTADO_API, ESTADOS_ABIERTOS, SEGUNDOS_POR_HORA
from app.constants.indicadores import ESCALA_DEL_TIEMPO_PROMEDIO
from app.enums.alcance_indicadores import AlcanceIndicadores
from app.enums.categoria_filtro import CategoriaFiltro
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.tarjeta_codigo import TarjetaCodigo
from app.incidencias.domain.indicadores import (
    AlcanceDeIndicadores,
    AreaDeAlcance,
    CantidadPorCategoria,
    CantidadPorEstado,
    ResumenDeIpress,
    TarjetaDeIndicador,
)
from app.shared.permisos import cuenta_todas_las_areas

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from app.incidencias.domain.indicadores import FilaDistribucion, FilaResumen
    from app.shared.sesion import SesionActual

type ValorDeTarjeta = Callable[[FilaResumen], tuple[int, int | None]]

VALOR_DE_TARJETA: dict[TarjetaCodigo, ValorDeTarjeta] = {
    TarjetaCodigo.RECIBIDOS: lambda fila: (fila.recibidos, fila.recibidos_anterior),
    TarjetaCodigo.PENDIENTES: lambda fila: (fila.pendientes, None),
    TarjetaCodigo.EN_GESTION: lambda fila: (fila.en_gestion, None),
    TarjetaCodigo.POR_VENCER: lambda fila: (fila.por_vencer, None),
    TarjetaCodigo.VENCIDOS: lambda fila: (fila.vencidos, None),
    TarjetaCodigo.RESUELTOS: lambda fila: (fila.resueltos, fila.resueltos_anterior),
    TarjetaCodigo.SIN_CLASIFICAR: lambda fila: (fila.sin_clasificar, None),
    TarjetaCodigo.POR_REVISAR: lambda fila: (fila.por_revisar, None),
    TarjetaCodigo.SIN_TOMAR: lambda fila: (fila.sin_tomar, None),
    TarjetaCodigo.CORREGIDAS_A_CORRUPCION: lambda fila: (
        fila.corregidas_a_corrupcion,
        fila.corregidas_a_corrupcion_anterior,
    ),
}


def tarjeta_de(codigo: TarjetaCodigo, fila: FilaResumen) -> TarjetaDeIndicador:
    valor, anterior = VALOR_DE_TARJETA[codigo](fila)
    return TarjetaDeIndicador(codigo, valor, anterior)


def alcance_de(sesion: SesionActual) -> AlcanceDeIndicadores:
    if cuenta_todas_las_areas(sesion.roles):
        return AlcanceDeIndicadores(AlcanceIndicadores.TODO, None)
    area = AreaDeAlcance(sesion.area.codigo, sesion.area.nombre, sesion.area.tipo) if sesion.area is not None else None
    return AlcanceDeIndicadores(AlcanceIndicadores.AREA, area)


def sumar_por_estado(filas: Iterable[FilaDistribucion]) -> dict[EstadoIncidencia, int]:
    sumas: dict[EstadoIncidencia, int] = {}
    for fila in filas:
        sumas[fila.estado] = sumas.get(fila.estado, 0) + fila.cantidad
    return sumas


def sumar_por_categoria(filas: Iterable[FilaDistribucion]) -> dict[CategoriaIncidencia | None, int]:
    sumas: dict[CategoriaIncidencia | None, int] = {}
    for fila in filas:
        sumas[fila.categoria] = sumas.get(fila.categoria, 0) + fila.cantidad
    return sumas


def cantidades_por_categoria(
    cantidades: dict[CategoriaIncidencia | None, int], *, con_sin_categoria: bool
) -> tuple[CantidadPorCategoria, ...]:
    filas = [
        CantidadPorCategoria(CategoriaFiltro(CATEGORIA_API[categoria].value), cantidades.get(categoria, 0))
        for categoria in CategoriaIncidencia
    ]
    if con_sin_categoria:
        filas.append(CantidadPorCategoria(CategoriaFiltro.SIN_CATEGORIA, cantidades.get(None, 0)))
    return tuple(filas)


def cantidades_por_estado(cantidades: dict[EstadoIncidencia, int]) -> tuple[CantidadPorEstado, ...]:
    return tuple(CantidadPorEstado(ESTADO_API[estado], cantidades.get(estado, 0)) for estado in EstadoIncidencia)


def horas_promedio(segundos: float | None) -> float | None:
    if segundos is None:
        return None
    return math.floor(segundos / SEGUNDOS_POR_HORA * ESCALA_DEL_TIEMPO_PROMEDIO + 0.5) / ESCALA_DEL_TIEMPO_PROMEDIO


def resumir_ipress(distribucion: list[FilaDistribucion]) -> ResumenDeIpress:
    por_estado = sumar_por_estado(distribucion)
    return ResumenDeIpress(
        total=sum(fila.cantidad for fila in distribucion),
        abiertos=sum(por_estado.get(estado, 0) for estado in ESTADOS_ABIERTOS),
        en_gestion=por_estado.get(EstadoIncidencia.EN_GESTION, 0),
        resueltos=por_estado.get(EstadoIncidencia.RESUELTO, 0),
        archivados=por_estado.get(EstadoIncidencia.ARCHIVADO, 0),
        por_categoria=cantidades_por_categoria(sumar_por_categoria(distribucion), con_sin_categoria=True),
    )
