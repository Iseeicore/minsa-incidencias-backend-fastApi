import json
from pathlib import Path

import pytest

from tests.helpers.acceso_en_memoria import AreasEnMemoria, UsuariosDeAccesoEnMemoria
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import cabecera_de_cookie, un_usuario_gestionado, un_usuario_interno, una_sesion
from tests.helpers.contract import openapi_del_nodo, validar_contrato
from tests.helpers.fakes import SesionesEnMemoria
from tests.helpers.usuarios_en_memoria import UsuariosEnMemoria

CONTRATO_DEL_NODO = Path(__file__).parents[2] / "docs" / "contrato" / "v1.json"
ANA = "11111111-1111-4111-8111-111111111111"
ADMIN = una_sesion(correo="admin@minsa.gob.pe", roles=("ADMINISTRADOR",))
NUEVO = {"nombreCompleto": "Dora Nueva", "correo": "dora@minsa.gob.pe", "rol": "GESTOR", "area": "HOSP-01"}
CREDENCIALES = {"correo": "gestor@minsa.gob.pe", "password": "clave-correcta"}


def _almacen() -> UsuariosEnMemoria:
    return UsuariosEnMemoria([un_usuario_gestionado(ANA, "Ana Torres", "ana@minsa.gob.pe", "GESTOR", 1)])


@pytest.mark.parametrize(
    ("ruta", "metodo", "operacion"),
    [
        ("/auth/login", "post", "iniciarSesion"),
        ("/auth/logout", "post", "cerrarSesion"),
        ("/auth/me", "get", "consultarSesionActual"),
        ("/areas", "get", "listarAreas"),
        ("/usuarios", "get", "listarUsuarios"),
        ("/usuarios", "post", "crearUsuario"),
        ("/usuarios/{id}", "patch", "actualizarUsuario"),
        ("/usuarios/{id}/restablecer-clave", "post", "restablecerClaveDeUsuario"),
    ],
)
def test_las_operaciones_existen_en_el_contrato_del_node_con_el_mismo_identificador(
    ruta: str, metodo: str, operacion: str
) -> None:
    contrato = json.loads(CONTRATO_DEL_NODO.read_text(encoding="utf-8"))

    assert contrato["paths"][ruta][metodo]["operationId"] == operacion


async def test_me_cumple_el_contrato() -> None:
    async with un_cliente(un_contenedor(), con_sesion=True) as cliente:
        validar_contrato(openapi_del_nodo(), await cliente.get("/v1/auth/me"))


async def test_me_sin_sesion_cumple_el_contrato() -> None:
    async with un_cliente(un_contenedor(), con_sesion=False) as cliente:
        validar_contrato(openapi_del_nodo(), await cliente.get("/v1/auth/me"))


async def test_el_login_y_el_logout_cumplen_el_contrato() -> None:
    contenedor = un_contenedor(usuarios_de_acceso=UsuariosDeAccesoEnMemoria([un_usuario_interno()]))
    async with un_cliente(contenedor, con_sesion=False) as cliente:
        validar_contrato(openapi_del_nodo(), await cliente.post("/v1/auth/login", json=CREDENCIALES))
        validar_contrato(
            openapi_del_nodo(), await cliente.post("/v1/auth/login", json={**CREDENCIALES, "password": "mal"})
        )
        validar_contrato(openapi_del_nodo(), await cliente.post("/v1/auth/login", json={"correo": "x"}))
        validar_contrato(openapi_del_nodo(), await cliente.post("/v1/auth/logout"))


async def test_las_areas_cumplen_el_contrato() -> None:
    async with un_cliente(un_contenedor(areas=AreasEnMemoria([]))) as cliente:
        validar_contrato(openapi_del_nodo(), await cliente.get("/v1/areas"))
        validar_contrato(openapi_del_nodo(), await cliente.get("/v1/areas", params={"limite": 0}))


async def test_los_usuarios_cumplen_el_contrato() -> None:
    contenedor = un_contenedor(usuarios=_almacen())
    async with un_cliente(contenedor, sesion=ADMIN) as cliente:
        validar_contrato(openapi_del_nodo(), await cliente.get("/v1/usuarios"))
        validar_contrato(openapi_del_nodo(), await cliente.post("/v1/usuarios", json=NUEVO))
        validar_contrato(openapi_del_nodo(), await cliente.post("/v1/usuarios", json=NUEVO))
        validar_contrato(openapi_del_nodo(), await cliente.patch(f"/v1/usuarios/{ANA}", json={"activo": False}))
        validar_contrato(openapi_del_nodo(), await cliente.patch(f"/v1/usuarios/{ANA}", json={}))
        validar_contrato(openapi_del_nodo(), await cliente.post(f"/v1/usuarios/{ANA}/restablecer-clave"))


async def test_un_usuario_ajeno_o_inexistente_cumple_el_contrato_de_404() -> None:
    contenedor = un_contenedor(usuarios=_almacen())
    async with un_cliente(contenedor, sesion=ADMIN) as cliente:
        desconocido = "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"
        validar_contrato(openapi_del_nodo(), await cliente.patch(f"/v1/usuarios/{desconocido}", json={"activo": False}))
        validar_contrato(openapi_del_nodo(), await cliente.post(f"/v1/usuarios/{desconocido}/restablecer-clave"))


async def test_los_usuarios_sin_permiso_o_sin_sesion_cumplen_el_contrato() -> None:
    async with un_cliente(un_contenedor(), sesion=una_sesion(roles=("GESTOR",))) as gestor:
        validar_contrato(openapi_del_nodo(), await gestor.get("/v1/usuarios"))
    async with un_cliente(un_contenedor(), con_sesion=False) as anonimo:
        validar_contrato(openapi_del_nodo(), await anonimo.get("/v1/usuarios"))
    contenedor = un_contenedor(resolvedor=SesionesEnMemoria())
    async with un_cliente(contenedor, con_sesion=False) as vencida:
        validar_contrato(
            openapi_del_nodo(),
            await vencida.get("/v1/usuarios", headers=cabecera_de_cookie("0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69")),
        )
