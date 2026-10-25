from typing import Annotated
from uuid import UUID

from fastapi import Path

from app.constants.incidencias import (
    ANIO_DEL_CODIGO_DIGITOS,
    PARTES_DEL_CODIGO,
    PREFIJO_CODIGO_INCIDENCIA,
    SECUENCIA_DEL_CODIGO_DIGITOS_MINIMOS,
)
from app.constants.textos.incidencias import MENSAJE_EVIDENCIA_NO_ENCONTRADA
from app.errors.no_encontrado import NoEncontrado


def _son_digitos(texto: str) -> bool:
    return texto.isascii() and texto.isdigit()


def codigo_de_incidencia(codigo: str) -> str:
    partes = codigo.split("-")
    es_valido = (
        len(partes) == PARTES_DEL_CODIGO
        and partes[0] == PREFIJO_CODIGO_INCIDENCIA
        and len(partes[1]) == ANIO_DEL_CODIGO_DIGITOS
        and _son_digitos(partes[1])
        and len(partes[2]) >= SECUENCIA_DEL_CODIGO_DIGITOS_MINIMOS
        and _son_digitos(partes[2])
    )
    if not es_valido:
        raise NoEncontrado
    return codigo


def identificador_de_evidencia(evidencia_id: Annotated[str, Path(alias="evidenciaId")]) -> str:
    try:
        canonico = str(UUID(evidencia_id))
    except ValueError:
        raise NoEncontrado(MENSAJE_EVIDENCIA_NO_ENCONTRADA) from None
    if canonico != evidencia_id:
        raise NoEncontrado(MENSAJE_EVIDENCIA_NO_ENCONTRADA)
    return evidencia_id
