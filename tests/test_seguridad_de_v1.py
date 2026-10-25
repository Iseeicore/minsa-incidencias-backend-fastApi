from http import HTTPStatus
from urllib.parse import quote

from app.shared.rate_limit import RateLimitPolicies
from app.shared.session_cookie import clear_cookie_header
from app.shared.signed_cookie import sign
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import SECRETO_DE_PRUEBA, una_config_de_cookie, una_politica, una_seguridad, una_sesion
from tests.helpers.fakes import SesionesEnMemoria

RUTA = "/v1/catalogos/plazos"
ORIGEN = "https://app.minsa.gob.pe"
ID_DESCONOCIDO = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"


def _cookie(session_id: str) -> dict[str, str]:
    return {"Cookie": f"gestion_sid={quote(f's:{sign(session_id, SECRETO_DE_PRUEBA)}', safe='')}"}


async def test_una_cookie_con_sesion_vigente_abre_la_ruta_protegida() -> None:
    sesion = una_sesion()
    contenedor = un_contenedor(resolvedor=SesionesEnMemoria({sesion.sesion_id: sesion}))
    async with un_cliente(contenedor, con_sesion=False) as cliente:
        respuesta = await cliente.get(RUTA, headers=_cookie(sesion.sesion_id))

    assert respuesta.status_code == HTTPStatus.OK


async def test_una_cookie_con_sesion_vencida_responde_invalid_session_y_borra_la_cookie() -> None:
    async with un_cliente(un_contenedor(), con_sesion=False) as cliente:
        respuesta = await cliente.get(RUTA, headers=_cookie(ID_DESCONOCIDO))

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()["errorCode"] == "INVALID_SESSION"
    assert respuesta.headers["set-cookie"] == clear_cookie_header(una_config_de_cookie())


async def test_una_escritura_desde_un_origen_ajeno_se_rechaza_antes_de_llegar_a_la_ruta() -> None:
    async with un_cliente(un_contenedor(), cors_origins=(ORIGEN,)) as cliente:
        respuesta = await cliente.post("/v1/cualquiera", headers={"Origin": "https://malicioso.example"})

    assert respuesta.status_code == HTTPStatus.FORBIDDEN
    assert respuesta.json()["errorCode"] == "FORBIDDEN"


async def test_las_rutas_de_v1_informan_el_limite_de_peticiones() -> None:
    async with un_cliente(un_contenedor()) as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.headers["ratelimit-limit"] == "1000"
    assert respuesta.headers["ratelimit-remaining"] == "999"


async def test_al_agotar_la_cubeta_de_v1_responde_429_con_las_cabeceras_expuestas() -> None:
    politicas = RateLimitPolicies(authenticated=una_politica(1), anonymous=una_politica(1))
    contenedor = un_contenedor(seguridad=una_seguridad(politicas=politicas))
    async with un_cliente(contenedor) as cliente:
        await cliente.get(RUTA)
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert respuesta.json()["errorCode"] == "RATE_LIMITED"
    assert respuesta.headers["retry-after"]


async def test_la_salud_no_gasta_la_cubeta_ni_exige_origen() -> None:
    politicas = RateLimitPolicies(authenticated=una_politica(1), anonymous=una_politica(1))
    contenedor = un_contenedor(seguridad=una_seguridad(politicas=politicas))
    async with un_cliente(contenedor) as cliente:
        for _ in range(3):
            respuesta = await cliente.get("/salud")
            assert respuesta.status_code == HTTPStatus.OK
            assert "ratelimit-limit" not in respuesta.headers
