from typing import Annotated
from uuid import UUID

from fastapi import Query
from pydantic import StringConstraints

from app.constants.incidencias import AREA_CODIGO_LONGITUD_MAXIMA, TEXTO_BUSQUEDA_MAXIMO
from app.constants.textos.errores import MENSAJE_CURSOR_INVALIDO
from app.constants.usuarios import USUARIOS_CURSOR_LONGITUD_MAXIMA, USUARIOS_LIMITE_MAXIMO, USUARIOS_LIMITE_POR_DEFECTO
from app.errors.datos_invalidos import DatosInvalidos
from app.errors.no_encontrado import NoEncontrado
from app.shared.cursor import decode_uuid_cursor
from app.usuarios.domain.pedidos import ConsultaUsuarios

TextoDeFiltro = Annotated[str, StringConstraints(strip_whitespace=True, max_length=TEXTO_BUSQUEDA_MAXIMO)]
CodigoDeAreaDeFiltro = Annotated[str, StringConstraints(strip_whitespace=True, max_length=AREA_CODIGO_LONGITUD_MAXIMA)]


def consulta_de_usuarios(
    limite: Annotated[int, Query(ge=1, le=USUARIOS_LIMITE_MAXIMO)] = USUARIOS_LIMITE_POR_DEFECTO,
    cursor: Annotated[str | None, Query(max_length=USUARIOS_CURSOR_LONGITUD_MAXIMA)] = None,
    q: Annotated[TextoDeFiltro, Query()] = "",
    area: Annotated[CodigoDeAreaDeFiltro, Query()] = "",
) -> ConsultaUsuarios:
    posicion = None
    if cursor:
        posicion = decode_uuid_cursor(cursor)
        if posicion is None:
            raise DatosInvalidos(details=[{"path": "cursor", "message": MENSAJE_CURSOR_INVALIDO}])
    return ConsultaUsuarios(limite=limite, despues_de=posicion, texto=q or None, area=area or None)


def identificador_de_usuario(id: str) -> str:  # noqa: A002
    try:
        canonico = str(UUID(id))
    except ValueError:
        raise NoEncontrado from None
    if canonico != id:
        raise NoEncontrado
    return id
