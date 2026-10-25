import pytest
from starlette.types import Scope

from app.shared.client_ip import client_ip


def _scope(cliente: tuple[str, int] | None, reenviado: str | None = None) -> Scope:
    cabeceras = [(b"x-forwarded-for", reenviado.encode())] if reenviado is not None else []
    return {"type": "http", "headers": cabeceras, "client": cliente}


def test_sin_proxy_confiable_se_usa_la_direccion_del_socket() -> None:
    assert client_ip(_scope(("10.0.0.5", 4000), "203.0.113.9"), trust_proxy=False) == "10.0.0.5"


def test_con_proxy_confiable_se_usa_el_primer_valor_reenviado() -> None:
    assert client_ip(_scope(("10.0.0.5", 4000), "203.0.113.9, 10.0.0.1"), trust_proxy=True) == "203.0.113.9"


@pytest.mark.parametrize("reenviado", [None, "", " , 10.0.0.1"], ids=["sin-cabecera", "vacia", "primer-valor-vacio"])
def test_con_proxy_confiable_pero_sin_valor_util_cae_al_socket(reenviado: str | None) -> None:
    assert client_ip(_scope(("10.0.0.5", 4000), reenviado), trust_proxy=True) == "10.0.0.5"


def test_sin_cliente_la_direccion_es_desconocida() -> None:
    assert client_ip(_scope(None), trust_proxy=False) == "desconocida"
