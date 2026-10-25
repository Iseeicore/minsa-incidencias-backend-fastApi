from app.constants.incidencias import DERIVACION_DESCRIPCION_LONGITUD_MAXIMA, TEXTO_DE_REVISION_LONGITUD_MINIMA
from app.constants.textos.incidencias import MENSAJE_DESCRIPCION_DERIVACION_INVALIDA
from app.errors.datos_invalidos import DatosInvalidos


def descripcion_de_derivacion(texto: str) -> str:
    descripcion = texto.strip()
    if not TEXTO_DE_REVISION_LONGITUD_MINIMA <= len(descripcion) <= DERIVACION_DESCRIPCION_LONGITUD_MAXIMA:
        raise DatosInvalidos(MENSAJE_DESCRIPCION_DERIVACION_INVALIDA)
    return descripcion


def descripcion_si_se_envia(texto: str | None) -> str | None:
    return None if texto is None else descripcion_de_derivacion(texto)
