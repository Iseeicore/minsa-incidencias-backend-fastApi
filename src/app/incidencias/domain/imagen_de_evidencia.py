import base64
import binascii
from dataclasses import dataclass

from app.constants.incidencias import (
    CARACTERES_POR_BLOQUE_BASE64,
    INICIO_DE_DATA_URI,
    SUFIJO_DE_DATA_URI_BASE64,
    TIPOS_DE_IMAGEN_DE_EVIDENCIA,
)

SEPARADOR_DE_DATA_URI = ","


@dataclass(frozen=True, slots=True)
class ImagenDeEvidencia:
    tipo: str
    contenido: bytes


def _inicio_de(tipo: str) -> str:
    return f"{INICIO_DE_DATA_URI}{tipo}{SUFIJO_DE_DATA_URI_BASE64}"


LARGO_DEL_INICIO_DE_IMAGEN = max(len(_inicio_de(tipo)) for tipo in TIPOS_DE_IMAGEN_DE_EVIDENCIA)
INICIO_DE_IMAGEN_PERMITIDA = "^data:(" + "|".join(TIPOS_DE_IMAGEN_DE_EVIDENCIA) + ");base64,"


def leer_imagen_de_evidencia(ruta: str) -> ImagenDeEvidencia | None:
    separador = ruta.find(SEPARADOR_DE_DATA_URI)
    if separador < 0:
        return None
    inicio = ruta[: separador + 1]
    tipo = next((permitido for permitido in TIPOS_DE_IMAGEN_DE_EVIDENCIA if inicio == _inicio_de(permitido)), None)
    if tipo is None:
        return None
    datos = ruta[separador + 1 :]
    if not datos or len(datos) % CARACTERES_POR_BLOQUE_BASE64 != 0:
        return None
    try:
        contenido = base64.b64decode(datos, validate=True)
    except binascii.Error, ValueError:
        return None
    if base64.b64encode(contenido).decode() != datos:
        return None
    return ImagenDeEvidencia(tipo, contenido)
