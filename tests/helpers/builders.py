from app.nota.domain.codigo_nota import CodigoNota
from app.nota.domain.nota import Nota
from tests.helpers.fakes import AHORA_FIJA


def un_codigo(numero: int = 1) -> CodigoNota:
    return CodigoNota.desde_numero(numero)


def una_nota(numero: int = 1, titulo: str = "Titulo", contenido: str = "Contenido") -> Nota:
    return Nota.crear(un_codigo(numero), titulo, contenido, AHORA_FIJA)
