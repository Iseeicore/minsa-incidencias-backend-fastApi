from typing import Annotated

from fastapi import Query

from app.constants.derivaciones import (
    DERIVACIONES_CURSOR_LONGITUD_MAXIMA,
    DERIVACIONES_LIMITE_MAXIMO,
    DERIVACIONES_LIMITE_POR_DEFECTO,
)
from app.constants.incidencias import CATEGORIA_DESDE_API
from app.constants.textos.errores import MENSAJE_CURSOR_INVALIDO
from app.enums.categoria_api import CategoriaApi
from app.enums.situacion_derivacion import SituacionDerivacion
from app.incidencias.adapters.http.filtros import (
    Detalle,
    Recortado,
    Texto,
    campos_comunes,
    fallar_si_hay_errores,
)
from app.incidencias.domain.cursores import decodificar_cursor_de_derivacion
from app.incidencias.domain.derivaciones import ConsultaDeDerivaciones, FiltrosDeDerivaciones


def _filtros(  # noqa: PLR0913, PLR0917
    situacion: SituacionDerivacion | None,
    texto: str | None,
    establecimiento: str | None,
    categoria: CategoriaApi | None,
    desde: str | None,
    hasta: str | None,
    errores: list[Detalle],
) -> FiltrosDeDerivaciones:
    campos = campos_comunes(texto, establecimiento, desde, hasta, errores)
    return FiltrosDeDerivaciones(
        situacion=situacion,
        texto=campos.texto,
        establecimiento=campos.establecimiento,
        categoria=CATEGORIA_DESDE_API[categoria] if categoria is not None else None,
        desde=campos.desde,
        hasta=campos.hasta,
    )


def filtros_de_conteos_de_derivacion(  # noqa: PLR0913, PLR0917
    situacion: Annotated[SituacionDerivacion | None, Query()] = None,
    texto: Annotated[Texto | None, Query()] = None,
    establecimiento: Annotated[Recortado | None, Query()] = None,
    categoria: Annotated[CategoriaApi | None, Query()] = None,
    desde: Annotated[Recortado | None, Query()] = None,
    hasta: Annotated[Recortado | None, Query()] = None,
) -> FiltrosDeDerivaciones:
    errores: list[Detalle] = []
    filtros = _filtros(situacion, texto, establecimiento, categoria, desde, hasta, errores)
    fallar_si_hay_errores(errores)
    return filtros


def consulta_de_derivaciones(  # noqa: PLR0913, PLR0917
    situacion: Annotated[SituacionDerivacion | None, Query()] = None,
    texto: Annotated[Texto | None, Query()] = None,
    establecimiento: Annotated[Recortado | None, Query()] = None,
    categoria: Annotated[CategoriaApi | None, Query()] = None,
    desde: Annotated[Recortado | None, Query()] = None,
    hasta: Annotated[Recortado | None, Query()] = None,
    limite: Annotated[int, Query(ge=1, le=DERIVACIONES_LIMITE_MAXIMO)] = DERIVACIONES_LIMITE_POR_DEFECTO,
    cursor: Annotated[str | None, Query(max_length=DERIVACIONES_CURSOR_LONGITUD_MAXIMA)] = None,
) -> ConsultaDeDerivaciones:
    errores: list[Detalle] = []
    filtros = _filtros(situacion, texto, establecimiento, categoria, desde, hasta, errores)
    despues_de = None
    if cursor:
        despues_de = decodificar_cursor_de_derivacion(cursor)
        if despues_de is None:
            errores.append({"path": "cursor", "message": MENSAJE_CURSOR_INVALIDO})
    fallar_si_hay_errores(errores)
    return ConsultaDeDerivaciones(limite=limite, filtros=filtros, despues_de=despues_de)
