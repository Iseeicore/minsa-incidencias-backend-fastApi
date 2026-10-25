import base64
import binascii
from dataclasses import dataclass
from uuid import UUID

from app.constants.cursor import (
    BASE64_PADDING,
    BASE64_PADDING_MULTIPLE,
    BASE64URL_ALPHABET,
    CURSOR_ENTERO_DIGITOS_MAXIMOS,
    CURSOR_NOMBRE_LONGITUD_MAXIMA,
    CURSOR_NUL,
    CURSOR_PARTES_MINIMAS,
    CURSOR_SEPARATOR,
)
from app.constants.limits import PG_INT_MAX


@dataclass(frozen=True, slots=True)
class PosicionPorNombre[T]:
    nombre: str
    id: T


def encode_parts(parts: list[str]) -> str:
    return base64.urlsafe_b64encode(CURSOR_SEPARATOR.join(parts).encode()).decode().rstrip(BASE64_PADDING)


def decode_parts(cursor: str) -> list[str] | None:
    if not cursor or not set(cursor) <= BASE64URL_ALPHABET:
        return None
    padded = cursor + BASE64_PADDING * (-len(cursor) % BASE64_PADDING_MULTIPLE)
    try:
        return base64.urlsafe_b64decode(padded).decode().split(CURSOR_SEPARATOR)
    except binascii.Error, UnicodeDecodeError:
        return None


def _split_id_and_name(cursor: str) -> tuple[str, str] | None:
    parts = decode_parts(cursor)
    if parts is None or len(parts) < CURSOR_PARTES_MINIMAS:
        return None
    identifier, name = parts[0], CURSOR_SEPARATOR.join(parts[1:])
    if not name or len(name) > CURSOR_NOMBRE_LONGITUD_MAXIMA or CURSOR_NUL in name:
        return None
    return identifier, name


def encode_uuid_cursor(position: PosicionPorNombre[str]) -> str:
    return encode_parts([position.id, position.nombre])


def decode_uuid_cursor(cursor: str) -> PosicionPorNombre[str] | None:
    split = _split_id_and_name(cursor)
    if split is None:
        return None
    identifier, name = split
    try:
        canonical = str(UUID(identifier))
    except ValueError:
        return None
    return PosicionPorNombre(name, identifier) if canonical == identifier else None


def encode_int_cursor(position: PosicionPorNombre[int]) -> str:
    return encode_parts([str(position.id), position.nombre])


def decode_int_cursor(cursor: str) -> PosicionPorNombre[int] | None:
    split = _split_id_and_name(cursor)
    if split is None:
        return None
    identifier, name = split
    is_positive_integer = identifier.isascii() and identifier.isdigit() and not identifier.startswith("0")
    if not is_positive_integer or len(identifier) > CURSOR_ENTERO_DIGITOS_MAXIMOS:
        return None
    number = int(identifier)
    return PosicionPorNombre(name, number) if number <= PG_INT_MAX else None
