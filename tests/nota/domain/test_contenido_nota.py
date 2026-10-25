import pytest

from app.nota.domain.constantes import CONTENIDO_MAX_LENGTH
from app.nota.domain.contenido_nota import ContenidoNota
from app.nota.domain.errors.contenido_invalido import ContenidoInvalido


@pytest.mark.parametrize("valor", ["", "texto", "x" * CONTENIDO_MAX_LENGTH], ids=["vacio", "corto", "en-el-limite"])
def test_acepta_un_contenido_hasta_el_largo_maximo(valor: str) -> None:
    assert ContenidoNota(valor).valor == valor


def test_rechaza_un_contenido_mas_largo_que_el_maximo() -> None:
    with pytest.raises(ContenidoInvalido):
        ContenidoNota("x" * (CONTENIDO_MAX_LENGTH + 1))
