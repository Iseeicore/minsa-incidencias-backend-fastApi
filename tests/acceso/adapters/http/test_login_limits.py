from http import HTTPStatus

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.acceso.adapters.http.login_limits import LoginLimits
from app.shared.http_errors import register_error_handlers
from app.shared.token_bucket import TokenBucketLimiter
from tests.helpers.builders import una_politica, una_seguridad
from tests.helpers.fakes import FixedClock


def _cliente(por_correo: int, por_ip: int, limitador: TokenBucketLimiter | None = None) -> AsyncClient:
    app = FastAPI()
    register_error_handlers(app, FixedClock())
    seguridad = una_seguridad(login_por_correo=una_politica(por_correo), login_por_ip=una_politica(por_ip))

    @app.post("/login", dependencies=[Depends(LoginLimits(limitador or TokenBucketLimiter(lambda: 0.0), seguridad))])
    async def login() -> dict[str, bool]:
        return {"ok": True}

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://prueba")


async def test_cada_intento_informa_lo_que_queda_del_limite_por_correo() -> None:
    async with _cliente(por_correo=5, por_ip=30) as cliente:
        primero = await cliente.post("/login", json={"correo": "ana@minsa.gob.pe"})
        segundo = await cliente.post("/login", json={"correo": "ana@minsa.gob.pe"})

    assert (primero.headers["ratelimit-limit"], primero.headers["ratelimit-remaining"]) == ("5", "4")
    assert segundo.headers["ratelimit-remaining"] == "3"


async def test_al_pasar_el_limite_por_correo_responde_429_con_retry_after() -> None:
    async with _cliente(por_correo=2, por_ip=30) as cliente:
        for _ in range(2):
            await cliente.post("/login", json={"correo": "ana@minsa.gob.pe"})
        respuesta = await cliente.post("/login", json={"correo": "ana@minsa.gob.pe"})

    assert respuesta.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert respuesta.json()["errorCode"] == "RATE_LIMITED"
    assert int(respuesta.headers["retry-after"]) >= 1
    assert respuesta.headers["ratelimit-remaining"] == "0"


async def test_el_correo_se_cuenta_sin_distinguir_mayusculas_ni_espacios() -> None:
    async with _cliente(por_correo=2, por_ip=30) as cliente:
        await cliente.post("/login", json={"correo": "ANA@minsa.gob.pe"})
        await cliente.post("/login", json={"correo": "  ana@minsa.gob.pe "})
        respuesta = await cliente.post("/login", json={"correo": "Ana@Minsa.gob.pe"})

    assert respuesta.status_code == HTTPStatus.TOO_MANY_REQUESTS


async def test_otro_correo_tiene_su_propia_cubeta() -> None:
    async with _cliente(por_correo=1, por_ip=30) as cliente:
        await cliente.post("/login", json={"correo": "ana@minsa.gob.pe"})
        respuesta = await cliente.post("/login", json={"correo": "luis@minsa.gob.pe"})

    assert respuesta.status_code == HTTPStatus.OK


async def test_el_limite_por_ip_se_agota_aunque_cambie_el_correo() -> None:
    async with _cliente(por_correo=10, por_ip=2) as cliente:
        await cliente.post("/login", json={"correo": "a@minsa.gob.pe"})
        await cliente.post("/login", json={"correo": "b@minsa.gob.pe"})
        respuesta = await cliente.post("/login", json={"correo": "c@minsa.gob.pe"})

    assert respuesta.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert respuesta.headers["ratelimit-limit"] == "2"


async def test_sin_correo_legible_se_cuenta_por_ip() -> None:
    async with _cliente(por_correo=2, por_ip=30) as cliente:
        await cliente.post("/login", content="no es json", headers={"Content-Type": "application/json"})
        await cliente.post("/login", json=["no", "es", "objeto"])
        await cliente.post("/login", json={"correo": 12})
        respuesta = await cliente.post("/login", json={"correo": "   "})

    assert respuesta.status_code == HTTPStatus.TOO_MANY_REQUESTS


async def test_los_intentos_sin_correo_no_gastan_la_cubeta_de_un_correo_real() -> None:
    async with _cliente(por_correo=1, por_ip=30) as cliente:
        await cliente.post("/login", json={})
        respuesta = await cliente.post("/login", json={"correo": "ana@minsa.gob.pe"})

    assert respuesta.status_code == HTTPStatus.OK
