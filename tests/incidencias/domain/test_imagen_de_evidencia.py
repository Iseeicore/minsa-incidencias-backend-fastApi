import base64

import pytest

from app.incidencias.domain.imagen_de_evidencia import (
    INICIO_DE_IMAGEN_PERMITIDA,
    LARGO_DEL_INICIO_DE_IMAGEN,
    leer_imagen_de_evidencia,
)
from tests.helpers.casos import IMAGEN_PNG, PNG_BASE64

BYTES = b"contenido-de-prueba"
BASE64 = base64.b64encode(BYTES).decode()


@pytest.mark.parametrize("tipo", ["image/jpeg", "image/png", "image/webp"])
def test_lee_las_imagenes_permitidas_guardadas_como_data_uri(tipo: str) -> None:
    imagen = leer_imagen_de_evidencia(f"data:{tipo};base64,{BASE64}")

    assert imagen is not None
    assert (imagen.tipo, imagen.contenido) == (tipo, BYTES)


def test_lee_un_png_real() -> None:
    imagen = leer_imagen_de_evidencia(IMAGEN_PNG)

    assert imagen is not None
    assert imagen.contenido == base64.b64decode(PNG_BASE64)
    assert imagen.contenido.startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "ruta",
    [
        "",
        "rutas-privadas/archivo.jpg",
        f"data:image/gif;base64,{BASE64}",
        f"data:text/html;base64,{BASE64}",
        f"data:image/png;charset=utf-8;base64,{BASE64}",
        f"DATA:image/png;base64,{BASE64}",
        "data:image/png;base64,",
        "data:image/png;base64",
        f"data:image/png;base64,{BASE64[:-1]}",
        f"data:image/png;base64,{BASE64}\n",
        "data:image/png;base64,@@@@",
        "data:image/png;base64,AB=C",
        "data:image/png;base64,YQ=",
        "data:image/png;base64,YR==",
    ],
    ids=lambda ruta: ruta[:40] or "vacia",
)
def test_rechaza_lo_que_no_es_una_imagen_en_data_uri_base64_canonico(ruta: str) -> None:
    assert leer_imagen_de_evidencia(ruta) is None


def test_el_inicio_permitido_y_su_largo_cubren_los_tres_tipos() -> None:
    assert INICIO_DE_IMAGEN_PERMITIDA == "^data:(image/jpeg|image/png|image/webp);base64,"
    assert len("data:image/jpeg;base64,") == LARGO_DEL_INICIO_DE_IMAGEN
