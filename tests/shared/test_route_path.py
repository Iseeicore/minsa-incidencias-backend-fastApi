import pytest
from starlette.types import Scope

from app.shared.route_path import is_logout, route_path


def _scope(metodo: str, ruta: str, raiz: str = "") -> Scope:
    return {"type": "http", "method": metodo, "path": ruta, "root_path": raiz}


def test_la_ruta_se_mide_sin_el_prefijo_de_montaje() -> None:
    assert route_path(_scope("GET", "/v1/auth/logout", "/v1")) == "/auth/logout"


def test_sin_prefijo_de_montaje_la_ruta_queda_igual() -> None:
    assert route_path(_scope("GET", "/auth/logout")) == "/auth/logout"


def test_si_la_ruta_no_empieza_con_el_prefijo_queda_igual() -> None:
    assert route_path(_scope("GET", "/otra", "/v1")) == "/otra"


@pytest.mark.parametrize(
    ("metodo", "ruta", "esperado"),
    [
        ("POST", "/v1/auth/logout", True),
        ("GET", "/v1/auth/logout", False),
        ("POST", "/v1/auth/login", False),
        ("POST", "/v1/auth/logout/otro", False),
    ],
)
def test_solo_el_post_de_cierre_de_sesion_es_cierre(metodo: str, ruta: str, esperado: bool) -> None:  # noqa: FBT001
    assert is_logout(_scope(metodo, ruta, "/v1")) is esperado
