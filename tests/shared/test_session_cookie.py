from email.utils import parsedate_to_datetime

import pytest

from app.shared.session_cookie import SessionCookieConfig, clear_cookie_header, read_session_id, set_cookie_header
from app.shared.signed_cookie import sign
from tests.helpers.vectores import vectores_del_nodo

VECTORES = vectores_del_nodo()
SECRETOS = (VECTORES["secreto"], VECTORES["anterior"])
DESARROLLO = SessionCookieConfig(secrets=SECRETOS, production=False)
PRODUCCION = SessionCookieConfig(secrets=SECRETOS, production=True)
ID_VALIDO = VECTORES["firmas"][0]["id"]


def _atributo(set_cookie: str, nombre: str) -> str:
    return next(parte.split("=", 1)[1] for parte in set_cookie.split("; ") if parte.startswith(f"{nombre}="))


@pytest.mark.parametrize("vector", VECTORES["firmas"], ids=lambda vector: vector["id"])
@pytest.mark.parametrize(("posicion", "config"), [(0, DESARROLLO), (1, PRODUCCION)], ids=["desarrollo", "produccion"])
def test_la_cabecera_set_cookie_es_identica_a_la_de_express(
    vector: dict[str, object], posicion: int, config: SessionCookieConfig
) -> None:
    esperado = vector["setCookie"][posicion]  # type: ignore[index]
    vence = parsedate_to_datetime(_atributo(esperado, "Expires"))

    obtenido = set_cookie_header(str(vector["id"]), config, int(_atributo(esperado, "Max-Age")), vence)

    assert obtenido == esperado


@pytest.mark.parametrize(("posicion", "config"), [(0, DESARROLLO), (1, PRODUCCION)], ids=["desarrollo", "produccion"])
def test_la_cabecera_que_borra_la_cookie_es_identica_a_la_de_express(
    posicion: int, config: SessionCookieConfig
) -> None:
    assert clear_cookie_header(config) == VECTORES["borrado"][posicion]


def test_el_nombre_depende_del_ambiente() -> None:
    assert DESARROLLO.name == "gestion_sid"
    assert PRODUCCION.name == "__Host-gestion_sid"


@pytest.mark.parametrize("lectura", VECTORES["lecturas"], ids=lambda lectura: lectura["nombre"])
def test_el_id_de_sesion_se_lee_como_lo_hace_el_node(lectura: dict[str, object]) -> None:
    cookies = dict([str(lectura["cookie"]).split("=", 1)])
    esperado = ID_VALIDO if lectura["nombre"] in {"actual", "anterior", "sinCodificar"} else None

    assert read_session_id(cookies, DESARROLLO) == esperado


def test_sin_cookie_no_hay_id() -> None:
    assert read_session_id({}, DESARROLLO) is None


def test_en_produccion_solo_se_lee_la_cookie_con_prefijo_host() -> None:
    cookies = {"gestion_sid": f"s:{sign(ID_VALIDO, SECRETOS[0])}"}

    assert read_session_id(cookies, PRODUCCION) is None


@pytest.mark.parametrize(
    ("candidato", "valido"),
    [
        ("00000000-0000-0000-0000-000000000000", True),
        ("ffffffff-ffff-ffff-ffff-ffffffffffff", True),
        ("0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69", True),
        ("0B9F8C9E-7D0A-4F5B-9A3C-1E2D3C4B5A69", True),
        ("018f3c2e-0000-7000-8000-000000000001", True),
        ("0b9f8c9e-7d0a-9f5b-9a3c-1e2d3c4b5a69", False),
        ("0b9f8c9e-7d0a-4f5b-0a3c-1e2d3c4b5a69", False),
        ("0b9f8c9e-7d0a-8f5b-ca3c-1e2d3c4b5a69", False),
        ("0b9f8c9e7d0a4f5b9a3c1e2d3c4b5a69", False),
        ("{0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69}", False),
        ("0b9f8c9e-7d0a-0f5b-9a3c-1e2d3c4b5a69", False),
        ("0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a6", False),
    ],
)
def test_el_id_valido_es_el_mismo_que_acepta_zod(candidato: str, valido: bool) -> None:  # noqa: FBT001
    cookies = {"gestion_sid": f"s:{sign(candidato, SECRETOS[0])}"}

    assert (read_session_id(cookies, DESARROLLO) == candidato) is valido
