from urllib.parse import unquote

import pytest

from app.shared.signed_cookie import read_signed, sign, unsign
from tests.helpers.vectores import vectores_del_nodo

VECTORES = vectores_del_nodo()
SECRETOS = [VECTORES["secreto"], VECTORES["anterior"]]


def _valor_de(set_cookie: str) -> str:
    return unquote(set_cookie.split(";", maxsplit=1)[0].split("=", 1)[1])


@pytest.mark.parametrize("vector", VECTORES["firmas"], ids=lambda vector: vector["id"])
def test_la_firma_es_la_misma_que_produce_cookie_parser(vector: dict[str, object]) -> None:
    esperado = _valor_de(vector["setCookie"][0])  # type: ignore[index]

    assert f"s:{sign(str(vector['id']), VECTORES['secreto'])}" == esperado


@pytest.mark.parametrize("lectura", VECTORES["lecturas"], ids=lambda lectura: lectura["nombre"])
def test_la_lectura_coincide_con_la_de_cookie_parser(lectura: dict[str, object]) -> None:
    crudo = str(lectura["cookie"]).split("=", 1)[1]
    esperado = lectura["firmada"] if isinstance(lectura["firmada"], str) else None

    assert read_signed(crudo, SECRETOS) == esperado


def test_una_firma_de_otro_secreto_no_valida() -> None:
    assert unsign(sign("valor", "uno"), "otro") is None


def test_un_valor_sin_firma_no_valida() -> None:
    assert unsign("valor-sin-punto", "uno") is None


def test_solo_el_primer_secreto_firma_pero_todos_validan() -> None:
    firmado_con_el_anterior = f"s:{sign('valor', VECTORES['anterior'])}"

    assert read_signed(firmado_con_el_anterior, SECRETOS) == "valor"
    assert read_signed(firmado_con_el_anterior, SECRETOS[:1]) is None
