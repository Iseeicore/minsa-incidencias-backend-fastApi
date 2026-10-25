from datetime import UTC, datetime

from app.constants.incidencias import (
    MICROSEGUNDOS_POR_MILISEGUNDO,
    SEGUNDOS_POR_HORA,
    UTC_OFFSET_SUFFIX,
    ZULU_SUFFIX,
)


def horas_entre(desde: datetime, hasta: datetime) -> int:
    return int((hasta - desde).total_seconds() // SEGUNDOS_POR_HORA)


def a_iso(instante: datetime) -> str:
    utc = instante.astimezone(UTC)
    return utc.isoformat(timespec="milliseconds").replace(UTC_OFFSET_SUFFIX, ZULU_SUFFIX)


def a_milisegundos(instante: datetime) -> datetime:
    return instante.replace(
        microsecond=instante.microsecond // MICROSEGUNDOS_POR_MILISEGUNDO * MICROSEGUNDOS_POR_MILISEGUNDO
    )
