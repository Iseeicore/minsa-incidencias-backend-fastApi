from typing import Annotated

from fastapi import Query

from app.constants.areas import AREAS_CURSOR_LONGITUD_MAXIMA, AREAS_LIMITE_MAXIMO, AREAS_LIMITE_POR_DEFECTO
from app.constants.textos.errores import MENSAJE_CURSOR_INVALIDO
from app.errors.datos_invalidos import DatosInvalidos
from app.incidencias.adapters.http.filtros import Texto
from app.incidencias.domain.ipress import ConsultaDeIpress
from app.shared.cursor import decode_int_cursor


def consulta_de_ipress(
    q: Annotated[Texto | None, Query()] = None,
    limite: Annotated[int, Query(ge=1, le=AREAS_LIMITE_MAXIMO)] = AREAS_LIMITE_POR_DEFECTO,
    cursor: Annotated[str | None, Query(max_length=AREAS_CURSOR_LONGITUD_MAXIMA)] = None,
) -> ConsultaDeIpress:
    posicion = None
    if cursor:
        posicion = decode_int_cursor(cursor)
        if posicion is None:
            raise DatosInvalidos(details=[{"path": "cursor", "message": MENSAJE_CURSOR_INVALIDO}])
    return ConsultaDeIpress(limite=limite, despues_de=posicion, texto=q or None)
