import pytest

from app.nota.domain.constantes import TITULO_MAX_LENGTH
from app.nota.domain.errors.titulo_invalido import TituloInvalido
from app.nota.domain.titulo_nota import TituloNota


def test_quita_los_espacios_de_los_extremos() -> None:
    assert TituloNota("  Reunión  ").valor == "Reunión"


def test_acepta_un_titulo_con_el_largo_maximo() -> None:
    assert len(TituloNota("x" * TITULO_MAX_LENGTH).valor) == TITULO_MAX_LENGTH


@pytest.mark.parametrize("valor", ["", "   ", "x" * (TITULO_MAX_LENGTH + 1)], ids=["vacio", "solo-espacios", "largo"])
def test_rechaza_un_titulo_vacio_o_demasiado_largo(valor: str) -> None:
    with pytest.raises(TituloInvalido):
        TituloNota(valor)


def test_dos_titulos_con_el_mismo_valor_son_iguales() -> None:
    assert TituloNota(" Hola ") == TituloNota("Hola")
