from http import HTTPStatus

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.types import Scope

from app.constants.http import SESSION_STATE_KEY
from app.shared.rate_limit import RateLimitMiddleware, RateLimitPolicies, general_target, rate_limit_headers
from app.shared.token_bucket import BucketPolicy, TakeResult, TokenBucketLimiter
from tests.helpers.builders import una_politica, una_sesion
from tests.helpers.fakes import FixedClock

POLITICAS = RateLimitPolicies(authenticated=BucketPolicy(300, 300), anonymous=BucketPolicy(100, 300))


def _scope(sesion: object | None = None, reenviado: str | None = None) -> Scope:
    cabeceras = [(b"x-forwarded-for", reenviado.encode())] if reenviado else []
    estado = {SESSION_STATE_KEY: sesion} if sesion is not None else {}
    return {"type": "http", "headers": cabeceras, "client": ("10.0.0.5", 4000), "state": estado}


def test_con_sesion_la_cubeta_es_del_usuario_y_usa_la_politica_autenticada() -> None:
    objetivo = general_target(_scope(una_sesion()), POLITICAS, trust_proxy=False)

    assert objetivo.key == f"usuario:{una_sesion().usuario_id}"
    assert objetivo.policy == POLITICAS.authenticated


def test_sin_sesion_la_cubeta_es_de_la_ip_y_usa_la_politica_anonima() -> None:
    objetivo = general_target(_scope(), POLITICAS, trust_proxy=False)

    assert objetivo.key == "ip:10.0.0.5"
    assert objetivo.policy == POLITICAS.anonymous


def test_con_proxy_confiable_la_ip_es_la_reenviada() -> None:
    assert general_target(_scope(reenviado="203.0.113.9"), POLITICAS, trust_proxy=True).key == "ip:203.0.113.9"


def test_las_cabeceras_informan_el_limite_y_lo_que_queda() -> None:
    assert rate_limit_headers(TakeResult(allowed=True, limit=100, remaining=99, retry_after_seconds=0)) == {
        "RateLimit-Limit": "100",
        "RateLimit-Remaining": "99",
    }


def _cliente(capacidad: int) -> AsyncClient:
    app = FastAPI()

    @app.get("/ping")
    @app.post("/auth/logout")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    politicas = RateLimitPolicies(authenticated=una_politica(capacidad), anonymous=una_politica(capacidad))
    limitador = TokenBucketLimiter(lambda: 0.0)
    app.add_middleware(
        RateLimitMiddleware, limiter=limitador, policies=politicas, clock=FixedClock(), trust_proxy=False
    )
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://prueba")


async def test_cada_respuesta_informa_el_limite_y_los_tokens_restantes() -> None:
    async with _cliente(capacidad=3) as cliente:
        primera = await cliente.get("/ping")
        segunda = await cliente.get("/ping")

    assert (primera.headers["ratelimit-limit"], primera.headers["ratelimit-remaining"]) == ("3", "2")
    assert segunda.headers["ratelimit-remaining"] == "1"


async def test_al_agotar_la_cubeta_responde_429_con_retry_after() -> None:
    async with _cliente(capacidad=2) as cliente:
        await cliente.get("/ping")
        await cliente.get("/ping")
        respuesta = await cliente.get("/ping")

    assert respuesta.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert respuesta.json()["errorCode"] == "RATE_LIMITED"
    assert respuesta.json()["message"] == "Demasiadas peticiones. Espera un momento e inténtalo de nuevo."
    assert respuesta.headers["ratelimit-limit"] == "2"
    assert respuesta.headers["ratelimit-remaining"] == "0"
    assert int(respuesta.headers["retry-after"]) >= 1


async def test_el_cierre_de_sesion_no_gasta_la_cubeta() -> None:
    async with _cliente(capacidad=1) as cliente:
        cierre = await cliente.post("/auth/logout")
        lectura = await cliente.get("/ping")

    assert cierre.status_code == HTTPStatus.OK
    assert "ratelimit-limit" not in cierre.headers
    assert lectura.status_code == HTTPStatus.OK
