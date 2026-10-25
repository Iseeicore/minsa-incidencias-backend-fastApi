import pytest

from app.catalogos.domain.codigo_renipress import codigo_renipress_buscado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("1234", "1234"), ("00001234", "1234"), (" 0012 ", "12"), ("0", "0"), ("000", "0"), ("10", "10")],
)
def test_un_texto_de_solo_digitos_se_busca_como_codigo_sin_ceros_a_la_izquierda(texto: str, esperado: str) -> None:
    assert codigo_renipress_buscado(texto) == esperado


@pytest.mark.parametrize("texto", ["", "hospital", "12a", "1 2", "-12", "\uff11\uff12"])
def test_un_texto_con_algo_que_no_es_digito_no_es_un_codigo(texto: str) -> None:
    assert codigo_renipress_buscado(texto) is None
