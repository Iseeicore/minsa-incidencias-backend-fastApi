from datetime import datetime

import pytest

from app.nota.domain.constantes import TITULO_MAX_LENGTH
from app.nota.domain.errors.fecha_sin_zona_horaria import FechaSinZonaHoraria
from app.nota.domain.errors.titulo_invalido import TituloInvalido
from app.nota.domain.nota import Nota
from tests.helpers.builders import un_codigo
from tests.helpers.fakes import AHORA_FIJA

AHORA = AHORA_FIJA


def test_crea_una_nota_con_la_fecha_recibida() -> None:
    nota = Nota.crear(un_codigo(), "Titulo", "Contenido", AHORA)

    assert nota.titulo.valor == "Titulo"
    assert nota.contenido.valor == "Contenido"
    assert nota.creada_en == AHORA


def test_quita_los_espacios_del_titulo() -> None:
    assert Nota.crear(un_codigo(), "  Titulo  ", "Contenido", AHORA).titulo.valor == "Titulo"


@pytest.mark.parametrize("titulo", ["", "   ", "x" * (TITULO_MAX_LENGTH + 1)])
def test_rechaza_un_titulo_vacio_o_demasiado_largo(titulo: str) -> None:
    with pytest.raises(TituloInvalido):
        Nota.crear(un_codigo(), titulo, "Contenido", AHORA)


def test_rechaza_una_fecha_sin_zona_horaria() -> None:
    with pytest.raises(FechaSinZonaHoraria):
        Nota.crear(un_codigo(), "Titulo", "Contenido", datetime(2026, 10, 24, 12, 0))  # noqa: DTZ001
