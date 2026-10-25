from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.constants.derivaciones import (
    IDENTIFICADOR_DE_DERIVACION_DIGITOS_MAXIMOS,
    MARCA_DE_DERIVACIONES,
    PARTES_CURSOR_DERIVACION,
)
from app.constants.incidencias import (
    MARCA_POR_VENCER,
    MARCA_VENCE_EN,
    PARTES_CURSOR_LISTADO,
    PARTES_CURSOR_POR_VENCER,
)
from app.constants.limits import PG_BIGINT_MAX
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


@dataclass(frozen=True, slots=True)
class PosicionDeDerivacion:
    fecha_derivacion: datetime
    id: str


def _instante(fecha: str) -> datetime | None:
    try:
        instante = datetime.fromisoformat(fecha).astimezone(UTC)
    except ValueError:
        return None
    return a_milisegundos(instante) if a_iso(instante) == fecha else None


def _instante_e_id(fecha: str, identificador: str) -> tuple[datetime, str] | None:
    try:
        canonico = str(UUID(identificador))
    except ValueError:
        return None
    instante = _instante(fecha)
    if instante is None or canonico != identificador.lower():
        return None
    return instante, identificador


def _es_identificador_de_derivacion(identificador: str) -> bool:
    es_positivo = identificador.isascii() and identificador.isdigit() and not identificador.startswith("0")
    return (
        es_positivo
        and len(identificador) <= IDENTIFICADOR_DE_DERIVACION_DIGITOS_MAXIMOS
        and int(identificador) <= PG_BIGINT_MAX
    )


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


def codificar_cursor_de_derivacion(posicion: PosicionDeDerivacion) -> str:
    return encode_parts([MARCA_DE_DERIVACIONES, a_iso(posicion.fecha_derivacion), posicion.id])


def decodificar_cursor_de_derivacion(cursor: str) -> PosicionDeDerivacion | None:
    partes = decode_parts(cursor)
    if partes is None or len(partes) != PARTES_CURSOR_DERIVACION or partes[0] != MARCA_DE_DERIVACIONES:
        return None
    instante = _instante(partes[1])
    if instante is None or not _es_identificador_de_derivacion(partes[2]):
        return None
    return PosicionDeDerivacion(instante, partes[2])
