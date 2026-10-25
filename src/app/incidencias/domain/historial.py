from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from app.constants.incidencias import (
    ACTOR_DESCONOCIDO,
    ACTOR_PREFIJO_SISTEMA,
    CATEGORIA_ETIQUETA,
    DIAS_HASTA_CAMBIAR_UNIDAD,
    HORAS_POR_DIA,
    NOMBRE_ACTOR_SISTEMA,
)
from app.constants.textos.incidencias import (
    CLASIFICADO_ETIQUETA,
    DETALLE_REGISTRADO,
    SIN_CATEGORIA_ETIQUETA,
    TITULO_ARCHIVADO,
    TITULO_CATEGORIA_CONFIRMADA,
    TITULO_CATEGORIA_CORREGIDA,
    TITULO_CLASIFICACION_INICIAL,
    TITULO_DERIVADO,
    TITULO_REABIERTO,
    TITULO_RECIBIDO_POR,
    TITULO_RESUELTO,
    TITULO_TOMADO,
    detalle_con_motivo,
    detalle_de_uno_a_otro,
    detalle_hacia,
    detalle_por_actor,
    texto_hace_dias,
    texto_hace_horas,
    texto_hace_menos_de_una_hora,
)
from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.domain.fila_historial import FilaHistorial, ItemDeHistorial
from app.incidencias.domain.tiempo import a_iso, horas_entre

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from datetime import datetime

    from app.enums.categoria_incidencia import CategoriaIncidencia

OPERACION_CREACION = "CREACION"
HORAS_HASTA_CONTAR_EN_DIAS = HORAS_POR_DIA * DIAS_HASTA_CAMBIAR_UNIDAD


@dataclass(frozen=True, slots=True)
class Hito:
    titulo: str
    detalle: str


def texto_hace(horas: int) -> str:
    if horas < 1:
        return texto_hace_menos_de_una_hora()
    if horas < HORAS_HASTA_CONTAR_EN_DIAS:
        return texto_hace_horas(horas)
    return texto_hace_dias(horas // HORAS_POR_DIA)


def _quien_hizo(fila: FilaHistorial) -> str:
    if fila.actor_nombre:
        return fila.actor_nombre
    return NOMBRE_ACTOR_SISTEMA if fila.actor.startswith(ACTOR_PREFIJO_SISTEMA) else ACTOR_DESCONOCIDO


def _etiqueta(categoria: CategoriaIncidencia | None) -> str:
    return CATEGORIA_ETIQUETA[categoria] if categoria is not None else SIN_CATEGORIA_ETIQUETA


def _detalle_de_la_clasificacion(fila: FilaHistorial) -> str:
    texto = _etiqueta(fila.categoria_ia) if fila.categoria_ia is not None else CLASIFICADO_ETIQUETA
    if fila.version:
        texto += f" (clasificador {fila.version})"
    return f"{texto}."


def _con_motivo(detalle: str, fila: FilaHistorial) -> str:
    return detalle_con_motivo(detalle, fila.descripcion_derivacion) if fila.descripcion_derivacion else detalle


def _hecho_por(titulo: str) -> Callable[[FilaHistorial], Hito]:
    return lambda fila: Hito(titulo, detalle_por_actor(_quien_hizo(fila)))


def _destino_de_la_derivacion(fila: FilaHistorial) -> str:
    destino = fila.area_despues or ""
    if fila.area_antes:
        return detalle_de_uno_a_otro(fila.area_antes, destino, _quien_hizo(fila))
    return detalle_hacia(destino, _quien_hizo(fila))


def _derivado_a_otra_area(fila: FilaHistorial) -> Hito:
    return Hito(TITULO_DERIVADO, _con_motivo(_destino_de_la_derivacion(fila), fila))


def _derivado_sin_cambio_de_area(fila: FilaHistorial) -> Hito:
    return Hito(TITULO_DERIVADO, _con_motivo(detalle_por_actor(_quien_hizo(fila)), fila))


def _categoria_corregida(fila: FilaHistorial) -> Hito:
    detalle = detalle_de_uno_a_otro(
        _etiqueta(fila.categoria_antes), _etiqueta(fila.categoria_despues), _quien_hizo(fila)
    )
    return Hito(TITULO_CATEGORIA_CORREGIDA, detalle)


REGLAS_DE_HITO: tuple[tuple[Callable[[FilaHistorial], bool], Callable[[FilaHistorial], Hito]], ...] = (
    (lambda fila: fila.resolvio, _hecho_por(TITULO_RESUELTO)),
    (lambda fila: fila.reabrio, _hecho_por(TITULO_REABIERTO)),
    (lambda fila: fila.estado_nuevo == EstadoIncidencia.ARCHIVADO, _hecho_por(TITULO_ARCHIVADO)),
    (lambda fila: fila.ia, lambda fila: Hito(TITULO_CLASIFICACION_INICIAL, _detalle_de_la_clasificacion(fila))),
    (lambda fila: bool(fila.area_despues) and fila.area_despues != fila.area_antes, _derivado_a_otra_area),
    (lambda fila: fila.estado_nuevo == EstadoIncidencia.DERIVADO, _derivado_sin_cambio_de_area),
    (lambda fila: fila.estado_nuevo == EstadoIncidencia.EN_GESTION, _hecho_por(TITULO_TOMADO)),
    (lambda fila: fila.corregida, _categoria_corregida),
    (lambda fila: fila.confirmada, _hecho_por(TITULO_CATEGORIA_CONFIRMADA)),
)


def _describir_hito(fila: FilaHistorial) -> Hito | None:
    for aplica, describe in REGLAS_DE_HITO:
        if aplica(fila):
            return describe(fila)
    return None


def construir_historial(filas: Sequence[FilaHistorial], canal: str, ahora: datetime) -> list[ItemDeHistorial]:
    items: list[ItemDeHistorial] = []
    ultima_descripcion: str | None = None
    for fila in filas:
        if fila.descripcion_derivacion is not None:
            ultima_descripcion = fila.descripcion_derivacion
        if fila.operacion == OPERACION_CREACION:
            hito: Hito | None = Hito(f"{TITULO_RECIBIDO_POR} {canal}", DETALLE_REGISTRADO)
        else:
            efectiva = fila.descripcion_derivacion if fila.descripcion_derivacion is not None else ultima_descripcion
            hito = _describir_hito(replace(fila, descripcion_derivacion=efectiva))
        if hito is None:
            continue
        hora = texto_hace(max(0, horas_entre(fila.fecha_hora, ahora)))
        items.append(ItemDeHistorial(hito.titulo, hito.detalle, hora, a_iso(fila.fecha_hora)))
    return items
