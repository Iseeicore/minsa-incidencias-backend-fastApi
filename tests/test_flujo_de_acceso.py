from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.composition import create_app
from app.config.settings import Settings
from app.shared.token_bucket import TokenBucketLimiter
from app.wiring import build_container
from tests.helpers.base import CLAVE_DE_PRUEBA, consultar, sembrar_area, sembrar_usuario

pytestmark = pytest.mark.integration

ORIGEN = "https://app.minsa.gob.pe"


def _cliente(engine: AsyncEngine) -> AsyncClient:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://u:c@localhost:1/b",
        cookie_secret="s" * 32,
        node_env="development",
        cors_origins=[ORIGEN],
    )
    app = create_app(build_container(settings, engine, TokenBucketLimiter()))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://prueba", headers={"Origin": ORIGEN})


async def _escenario(engine: AsyncEngine) -> None:
    await sembrar_area(engine, 10, "HOSP-01", "Hospital Uno")
    await sembrar_usuario(engine, "admin@minsa.gob.pe", "ADMINISTRADOR", None, nombre="Admin General")
    await sembrar_usuario(engine, "gestor@minsa.gob.pe", "GESTOR", 10, nombre="Gestor Uno")


async def test_el_ciclo_completo_de_acceso_con_la_base_real_y_un_hash_generado_por_el_node(engine: AsyncEngine) -> None:
    await _escenario(engine)
    credenciales = {"correo": "admin@minsa.gob.pe", "password": CLAVE_DE_PRUEBA}

    async with _cliente(engine) as cliente:
        sin_sesion = await cliente.get("/v1/auth/me")
        mala = await cliente.post("/v1/auth/login", json={**credenciales, "password": "incorrecta"})
        login = await cliente.post("/v1/auth/login", json=credenciales)
        perfil = await cliente.get("/v1/auth/me")
        usuarios = await cliente.get("/v1/usuarios")
        areas = await cliente.get("/v1/areas")
        cierre = await cliente.post("/v1/auth/logout")
        tras_el_cierre = await cliente.get("/v1/auth/me")

    assert sin_sesion.status_code == HTTPStatus.UNAUTHORIZED
    assert mala.status_code == HTTPStatus.UNAUTHORIZED
    assert login.status_code == HTTPStatus.NO_CONTENT
    assert perfil.status_code == HTTPStatus.OK
    assert perfil.json()["roles"] == ["ADMINISTRADOR"]
    assert perfil.json()["area"] is None
    assert usuarios.status_code == HTTPStatus.OK
    assert [u["correo"] for u in usuarios.json()["items"]] == ["admin@minsa.gob.pe", "gestor@minsa.gob.pe"]
    assert [a["codigo"] for a in areas.json()["items"]] == ["HOSP-01", "OTRANS"]
    assert cierre.status_code == HTTPStatus.NO_CONTENT
    assert tras_el_cierre.status_code == HTTPStatus.UNAUTHORIZED
    assert tras_el_cierre.json()["errorCode"] == "UNAUTHORIZED"


async def test_una_sesion_revocada_en_la_base_responde_invalid_session(engine: AsyncEngine) -> None:
    await _escenario(engine)

    async with _cliente(engine) as cliente:
        await cliente.post("/v1/auth/login", json={"correo": "admin@minsa.gob.pe", "password": CLAVE_DE_PRUEBA})
        async with engine.begin() as conexion:
            await conexion.execute(text("UPDATE gestion.sesion_usuario SET revocada_en = now()"))
        respuesta = await cliente.get("/v1/auth/me")

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
    assert respuesta.json()["errorCode"] == "INVALID_SESSION"
    assert "gestion_sid=" in respuesta.headers["set-cookie"]


async def test_el_gestor_no_tiene_la_vista_de_usuarios(engine: AsyncEngine) -> None:
    await _escenario(engine)

    async with _cliente(engine) as cliente:
        await cliente.post("/v1/auth/login", json={"correo": "gestor@minsa.gob.pe", "password": CLAVE_DE_PRUEBA})
        respuesta = await cliente.get("/v1/usuarios")
        areas = await cliente.get("/v1/areas")

    assert respuesta.status_code == HTTPStatus.FORBIDDEN
    assert areas.status_code == HTTPStatus.OK


async def test_crear_actualizar_y_restablecer_un_usuario_de_punta_a_punta(engine: AsyncEngine) -> None:
    await _escenario(engine)
    nuevo = {"nombreCompleto": "Dora Nueva", "correo": "dora@minsa.gob.pe", "rol": "ESTABLECIMIENTO", "area": "HOSP-01"}

    async with _cliente(engine) as cliente:
        await cliente.post("/v1/auth/login", json={"correo": "admin@minsa.gob.pe", "password": CLAVE_DE_PRUEBA})
        creado = await cliente.post("/v1/usuarios", json=nuevo)
        repetido = await cliente.post("/v1/usuarios", json=nuevo)
        identificador = creado.json()["usuario"]["id"]
        clave = creado.json()["claveInicial"]
        actualizado = await cliente.patch(f"/v1/usuarios/{identificador}", json={"nombreCompleto": "Dora Ruiz"})
        restablecido = await cliente.post(f"/v1/usuarios/{identificador}/restablecer-clave")
        desactivada = await cliente.patch(f"/v1/usuarios/{identificador}", json={"activo": False})

    assert creado.status_code == HTTPStatus.CREATED
    assert repetido.status_code == HTTPStatus.CONFLICT
    assert repetido.json()["errorCode"] == "CORREO_REPETIDO"
    assert actualizado.json()["usuario"]["nombreCompleto"] == "Dora Ruiz"
    assert restablecido.json()["claveInicial"] != clave
    assert desactivada.json()["usuario"]["activo"] is False
    auditoria = await consultar(
        engine,
        "SELECT usuario_creacion FROM gestion.usuario_interno WHERE correo = :correo",
        correo="dora@minsa.gob.pe",
    )
    assert auditoria == [("usuario:admin@minsa.gob.pe",)]
