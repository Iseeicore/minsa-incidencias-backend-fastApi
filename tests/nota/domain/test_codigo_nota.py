import pytest

from app.nota.domain.codigo_nota import CodigoNota
from app.nota.domain.errors.codigo_nota_invalido import CodigoNotaInvalido


@pytest.mark.parametrize("valor", ["NOTA-000001", "NOTA-123456"])
def test_acepta_un_codigo_con_el_formato_del_negocio(valor: str) -> None:
    assert CodigoNota(valor).valor == valor


@pytest.mark.parametrize(
    "valor",
    ["", "nota-000001", "NOTA-1", "NOTA-1234567", "OTRA-000001", " NOTA-000001", f"NOTA-{chr(0x660) * 5}{chr(0x661)}"],
)
def test_rechaza_un_codigo_con_otro_formato(valor: str) -> None:
    with pytest.raises(CodigoNotaInvalido):
        CodigoNota(valor)


def test_dos_codigos_con_el_mismo_valor_son_iguales() -> None:
    assert CodigoNota("NOTA-000007") == CodigoNota("NOTA-000007")


def test_arma_el_codigo_desde_un_numero() -> None:
    assert CodigoNota.desde_numero(42).valor == "NOTA-000042"
