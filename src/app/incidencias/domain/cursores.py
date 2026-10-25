from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.constants.incidencias import (
    MARCA_POR_VENCER,
    MARCA_VENCE_EN,
    PARTES_CURSOR_LISTADO,
    PARTES_CURSOR_POR_VENCER,
)
from app.incidencias.domain.tiempo import a_iso, a_milisegundos
from app.shared.cursor import decode_parts, encode_parts


@dataclass(frozen=True, slots=True)
class PosicionDeListado:
    fecha_creacion: datetime
    id: str


@dataclass(frozen=True, slots=True)
class PosicionPorVencer:
    vence_en: datetime
    id: str


def _instante_e_id(fecha: str, identificador: str) -> tuple[datetime, str] | None:
    try:
        instante = datetime.fromisoformat(fecha).astimezone(UTC)
        canonico = str(UUID(identificador))
    except ValueError:
        return None
    if a_iso(instante) != fecha or canonico != identificador.lower():
        return None
    return a_milisegundos(instante), identificador


def codificar_cursor(posicion: PosicionDeListado) -> str:
    return encode_parts([a_iso(posicion.fecha_creacion), posicion.id])


def decodificar_cursor(cursor: str) -> PosicionDeListado | None:
    partes = decode_parts(cursor)
    if partes is None or len(partes) != PARTES_CURSOR_LISTADO:
        return None
    posicion = _instante_e_id(partes[0], partes[1])
    return PosicionDeListado(posicion[0], posicion[1]) if posicion else None


def codificar_cursor_por_vencer(posicion: PosicionPorVencer) -> str:
    return encode_parts([MARCA_POR_VENCER, MARCA_VENCE_EN, a_iso(posicion.vence_en), posicion.id])


def decodificar_cursor_por_vencer(cursor: str) -> PosicionPorVencer | None:
    partes = decode_parts(cursor)
    if partes is None or len(partes) != PARTES_CURSOR_POR_VENCER:
        return None
    if partes[0] != MARCA_POR_VENCER or partes[1] != MARCA_VENCE_EN:
        return None
    posicion = _instante_e_id(partes[2], partes[3])
    return PosicionPorVencer(posicion[0], posicion[1]) if posicion else None
