from typing import Annotated

from fastapi import Query
from pydantic import StringConstraints

from app.constants.incidencias import (
    CURSOR_LONGITUD_MAXIMA,
    ESTADO_DESDE_API,
    ESTADOS_ABIERTOS,
    LISTADO_LIMITE_MAXIMO,
    LISTADO_LIMITE_POR_DEFECTO,
    LISTADO_RANGO_MAXIMO_DIAS,
    TEXTO_BUSQUEDA_MAXIMO,
)
from app.constants.textos.errores import MENSAJE_CURSOR_INVALIDO
from app.constants.textos.incidencias import (
    MENSAJE_ESTABLECIMIENTO_INVALIDO,
    MENSAJE_FECHA_INVALIDA,
    MENSAJE_PLAZO_SOLO_CASOS_ABIERTOS,
    MENSAJE_RANGO_INVERTIDO,
    mensaje_rango_demasiado_largo,
)
from app.enums.categoria_filtro import CategoriaFiltro
from app.enums.estado_api import EstadoApi
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.plazo_filtro import PlazoFiltro
from app.errors.datos_invalidos import DatosInvalidos
from app.incidencias.domain.consultas import ConsultaListado, FiltrosConsulta
from app.incidencias.domain.cursores import decodificar_cursor, decodificar_cursor_por_vencer
from app.incidencias.domain.rango_fechas import dia_de, dias_del_rango
from app.shared.codigo_renipress import codigo_renipress_canonico

Texto = Annotated[str, StringConstraints(strip_whitespace=True, max_length=TEXTO_BUSQUEDA_MAXIMO)]
Recortado = Annotated[str, StringConstraints(strip_whitespace=True)]
Detalle = dict[str, str]


def _dia(valor: str | None, ruta: str, errores: list[Detalle]) -> str | None:
    if not valor:
        return None
    if dia_de(valor) is None:
        errores.append({"path": ruta, "message": MENSAJE_FECHA_INVALIDA})
        return None
    return valor


def _establecimiento(valor: str | None, errores: list[Detalle]) -> str | None:
    if not valor:
        return None
    canonico = codigo_renipress_canonico(valor)
    if canonico is None:
        errores.append({"path": "establecimiento", "message": MENSAJE_ESTABLECIMIENTO_INVALIDO})
    return canonico


def _validar_rango(desde: str | None, hasta: str | None, errores: list[Detalle]) -> None:
    if not desde or not hasta:
        return
    dias = dias_del_rango(desde, hasta)
    if dias is None:
        return
    if dias < 1:
        errores.append({"path": "desde", "message": MENSAJE_RANGO_INVERTIDO})
    elif dias > LISTADO_RANGO_MAXIMO_DIAS:
        errores.append({"path": "hasta", "message": mensaje_rango_demasiado_largo(LISTADO_RANGO_MAXIMO_DIAS)})


def _validar_plazo(filtros: FiltrosConsulta, errores: list[Detalle]) -> None:
    if not filtros.por_vencer:
        return
    estado_cerrado = filtros.estado is not None and ESTADO_DESDE_API[filtros.estado] not in ESTADOS_ABIERTOS
    if estado_cerrado or filtros.motivo_archivo is not None:
        errores.append({"path": "plazo", "message": MENSAJE_PLAZO_SOLO_CASOS_ABIERTOS})


def armar_filtros(  # noqa: PLR0913, PLR0917
    estado: EstadoApi | None,
    motivo_archivo: MotivoArchivo | None,
    categoria: CategoriaFiltro | None,
    texto: str | None,
    establecimiento: str | None,
    desde: str | None,
    hasta: str | None,
    plazo: PlazoFiltro | None,
    errores: list[Detalle],
) -> FiltrosConsulta:
    dia_desde = _dia(desde, "desde", errores)
    dia_hasta = _dia(hasta, "hasta", errores)
    filtros = FiltrosConsulta(
        estado=estado,
        categoria=categoria,
        texto=texto or None,
        establecimiento=_establecimiento(establecimiento, errores),
        motivo_archivo=motivo_archivo,
        desde=dia_desde,
        hasta=dia_hasta,
        por_vencer=plazo is not None,
    )
    _validar_rango(dia_desde, dia_hasta, errores)
    _validar_plazo(filtros, errores)
    return filtros


def _fallar_si_hay_errores(errores: list[Detalle]) -> None:
    if errores:
        raise DatosInvalidos(details=errores)


def filtros_de_conteos(  # noqa: PLR0913, PLR0917
    estado: Annotated[EstadoApi | None, Query()] = None,
    motivo_archivo: Annotated[MotivoArchivo | None, Query(alias="motivoArchivo")] = None,
    categoria: Annotated[CategoriaFiltro | None, Query()] = None,
    texto: Annotated[Texto | None, Query()] = None,
    establecimiento: Annotated[Recortado | None, Query()] = None,
    desde: Annotated[Recortado | None, Query()] = None,
    hasta: Annotated[Recortado | None, Query()] = None,
    plazo: Annotated[PlazoFiltro | None, Query()] = None,
) -> FiltrosConsulta:
    errores: list[Detalle] = []
    filtros = armar_filtros(estado, motivo_archivo, categoria, texto, establecimiento, desde, hasta, plazo, errores)
    _fallar_si_hay_errores(errores)
    return filtros


def consulta_de_listado(  # noqa: PLR0913, PLR0917
    estado: Annotated[EstadoApi | None, Query()] = None,
    motivo_archivo: Annotated[MotivoArchivo | None, Query(alias="motivoArchivo")] = None,
    categoria: Annotated[CategoriaFiltro | None, Query()] = None,
    texto: Annotated[Texto | None, Query()] = None,
    establecimiento: Annotated[Recortado | None, Query()] = None,
    desde: Annotated[Recortado | None, Query()] = None,
    hasta: Annotated[Recortado | None, Query()] = None,
    plazo: Annotated[PlazoFiltro | None, Query()] = None,
    limite: Annotated[int, Query(ge=1, le=LISTADO_LIMITE_MAXIMO)] = LISTADO_LIMITE_POR_DEFECTO,
    cursor: Annotated[str | None, Query(max_length=CURSOR_LONGITUD_MAXIMA)] = None,
) -> ConsultaListado:
    errores: list[Detalle] = []
    filtros = armar_filtros(estado, motivo_archivo, categoria, texto, establecimiento, desde, hasta, plazo, errores)
    despues_de = None
    despues_de_por_vencer = None
    if cursor:
        despues_de_por_vencer = decodificar_cursor_por_vencer(cursor) if filtros.por_vencer else None
        despues_de = None if filtros.por_vencer else decodificar_cursor(cursor)
        if despues_de is None and despues_de_por_vencer is None:
            errores.append({"path": "cursor", "message": MENSAJE_CURSOR_INVALIDO})
    _fallar_si_hay_errores(errores)
    return ConsultaListado(
        limite=limite, filtros=filtros, despues_de=despues_de, despues_de_por_vencer=despues_de_por_vencer
    )
