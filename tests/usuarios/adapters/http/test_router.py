from dataclasses import replace
from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.shared.cursor import PosicionPorNombre, encode_uuid_cursor
from app.shared.sesion import SesionActual
from tests.helpers.acceso_en_memoria import HasherFalso
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_area_de_sesion, un_usuario_gestionado, una_sesion
from tests.helpers.usuarios_en_memoria import UsuariosEnMemoria

RUTA = "/v1/usuarios"
ANA = "11111111-1111-4111-8111-111111111111"
BRUNO = "22222222-2222-4222-8222-222222222222"
ADMIN = una_sesion(correo="admin@minsa.gob.pe", roles=("ADMINISTRADOR",))
JEFE = una_sesion(correo="jefe@minsa.gob.pe", roles=("ESTABLECIMIENTO",), area=un_area_de_sesion(id=1))
NUEVO = {"nombreCompleto": "Dora Nueva", "correo": "  DORA@minsa.gob.pe ", "rol": "GESTOR", "area": "HOSP-01"}


def _almacen() -> UsuariosEnMemoria:
    return UsuariosEnMemoria(
        [
            un_usuario_gestionado(ANA, "Ana Torres", "ana@minsa.gob.pe", "GESTOR", 1),
            un_usuario_gestionado(BRUNO, "Bruno Díaz", "bruno@minsa.gob.pe", "GESTOR", 2),
        ]
    )


def _cliente(
    almacen: UsuariosEnMemoria | None = None, sesion: SesionActual = ADMIN, *, con_sesion: bool = True
) -> AsyncClient:
    contenedor = un_contenedor(usuarios=almacen or _almacen(), hasher=HasherFalso())
    return un_cliente(contenedor, con_sesion=con_sesion, sesion=sesion)


async def test_listar_devuelve_la_pagina_con_la_forma_del_contrato() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(RUTA)

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == {
        "items": [
            {
                "id": ANA,
                "nombreCompleto": "Ana Torres",
                "correo": "ana@minsa.gob.pe",
                "rol": "GESTOR",
                "activo": True,
                "area": {"codigo": "HOSP-01", "nombre": "Hospital Uno"},
            },
            {
                "id": BRUNO,
                "nombreCompleto": "Bruno Díaz",
                "correo": "bruno@minsa.gob.pe",
                "rol": "GESTOR",
                "activo": True,
                "area": {"codigo": "HOSP-02", "nombre": "Hospital Dos"},
            },
        ],
        "siguiente": None,
        "hayMas": False,
    }


async def test_listar_pagina_con_limite_y_cursor() -> None:
    async with _cliente() as cliente:
        primera = await cliente.get(RUTA, params={"limite": 1})
        segunda = await cliente.get(RUTA, params={"limite": 1, "cursor": primera.json()["siguiente"]})

    assert primera.json()["hayMas"] is True
    assert [u["id"] for u in primera.json()["items"]] == [ANA]
    assert [u["id"] for u in segunda.json()["items"]] == [BRUNO]
    assert segunda.json()["siguiente"] is None


async def test_listar_filtra_por_texto_y_por_area_para_el_administrador() -> None:
    async with _cliente() as cliente:
        por_texto = await cliente.get(RUTA, params={"q": "  bruno "})
        por_area = await cliente.get(RUTA, params={"area": "HOSP-01"})

    assert [u["id"] for u in por_texto.json()["items"]] == [BRUNO]
    assert [u["id"] for u in por_area.json()["items"]] == [ANA]


async def test_listar_para_un_establecimiento_solo_trae_su_area() -> None:
    async with _cliente(sesion=JEFE) as cliente:
        respuesta = await cliente.get(RUTA)

    assert [u["id"] for u in respuesta.json()["items"]] == [ANA]


@pytest.mark.parametrize(
    ("params", "ruta"),
    [
        ({"limite": 0}, "limite"),
        ({"limite": 201}, "limite"),
        ({"limite": "abc"}, "limite"),
        ({"q": "x" * 101}, "q"),
        ({"area": "x" * 51}, "area"),
        ({"cursor": "x" * 601}, "cursor"),
    ],
)
async def test_listar_con_parametros_invalidos_responde_400_con_la_ruta_del_campo(
    params: dict[str, str | int], ruta: str
) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(RUTA, params=params)

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["errorCode"] == "VALIDATION_FAILED"
    assert [detalle["path"] for detalle in respuesta.json()["details"]] == [ruta]


@pytest.mark.parametrize("cursor", ["###", "no es base64!", encode_uuid_cursor(PosicionPorNombre("x", ANA))[:-4]])
async def test_listar_con_un_cursor_alterado_responde_400(cursor: str) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.get(RUTA, params={"cursor": cursor})

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["details"] == [{"path": "cursor", "message": "El cursor no es válido."}]


async def test_sin_sesion_responde_401_y_sin_la_vista_de_usuarios_403() -> None:
    async with _cliente(con_sesion=False) as sin_sesion:
        sin = await sin_sesion.get(RUTA)
    async with _cliente(sesion=una_sesion(roles=("GESTOR",))) as gestor:
        prohibido = await gestor.get(RUTA)

    assert sin.status_code == HTTPStatus.UNAUTHORIZED
    assert prohibido.status_code == HTTPStatus.FORBIDDEN
    assert prohibido.json()["errorCode"] == "FORBIDDEN"
    assert prohibido.json()["message"] == "No tienes permisos para esta acción."


async def test_crear_responde_201_con_el_usuario_y_la_clave_inicial_normalizando_el_correo() -> None:
    almacen = _almacen()
    async with _cliente(almacen) as cliente:
        respuesta = await cliente.post(RUTA, json=NUEVO)

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.CREATED
    assert cuerpo["usuario"]["correo"] == "dora@minsa.gob.pe"
    assert cuerpo["usuario"]["rol"] == "GESTOR"
    assert len(cuerpo["claveInicial"]) == 20
    assert respuesta.headers["cache-control"] == "no-store"
    assert len(almacen.usuarios) == 3


async def test_crear_con_un_correo_repetido_responde_409_correo_repetido() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post(RUTA, json={**NUEVO, "correo": "ana@minsa.gob.pe"})

    assert respuesta.status_code == HTTPStatus.CONFLICT
    assert respuesta.json()["errorCode"] == "CORREO_REPETIDO"
    assert respuesta.json()["message"] == "Ya existe un usuario con ese correo."


async def test_crear_con_un_area_inexistente_responde_422() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post(RUTA, json={**NUEVO, "area": "NO-EXISTE"})

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert respuesta.json()["errorCode"] == "UNPROCESSABLE"


@pytest.mark.parametrize(
    ("cambio", "ruta"),
    [
        ({"nombreCompleto": "ab"}, "nombreCompleto"),
        ({"nombreCompleto": "x" * 121}, "nombreCompleto"),
        ({"correo": "no-es-correo"}, "correo"),
        ({"rol": "DIRIS"}, "rol"),
        ({"area": ""}, "area"),
    ],
)
async def test_crear_con_datos_invalidos_responde_400_con_la_ruta_del_campo(cambio: dict[str, str], ruta: str) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post(RUTA, json={**NUEVO, **cambio})

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert ruta in {detalle["path"] for detalle in respuesta.json()["details"]}


async def test_crear_sin_la_vista_de_usuarios_responde_403_antes_de_validar_el_cuerpo() -> None:
    async with _cliente(sesion=una_sesion(roles=("GESTOR",))) as cliente:
        respuesta = await cliente.post(RUTA, json={})

    assert respuesta.status_code == HTTPStatus.FORBIDDEN


async def test_actualizar_responde_200_con_el_usuario_cambiado() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.patch(f"{RUTA}/{ANA}", json={"nombreCompleto": "Ana María", "activo": False})

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()["usuario"]["nombreCompleto"] == "Ana María"
    assert respuesta.json()["usuario"]["activo"] is False


@pytest.mark.parametrize("cuerpo", [{}, {"area": None}], ids=["vacio", "solo-nulos"])
async def test_actualizar_sin_ningun_dato_responde_400_con_el_mensaje_del_contrato(cuerpo: dict[str, None]) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.patch(f"{RUTA}/{ANA}", json=cuerpo)

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["details"] == [{"path": "", "message": "Indica al menos un dato para cambiar."}]


async def test_actualizar_con_un_activo_que_no_es_booleano_responde_400() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.patch(f"{RUTA}/{ANA}", json={"activo": "false"})

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.parametrize(
    "identificador", ["no-es-uuid", "0B9F8C9E-7D0A-4F5B-9A3C-1E2D3C4B5A69", "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"]
)
async def test_actualizar_un_id_que_no_existe_o_no_es_uuid_en_minusculas_responde_404(identificador: str) -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.patch(f"{RUTA}/{identificador}", json={"activo": False})

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["errorCode"] == "NOT_FOUND"


async def test_actualizarse_uno_mismo_el_rol_o_la_vigencia_responde_409() -> None:
    async with _cliente(sesion=replace(ADMIN, usuario_id=ANA)) as cliente:
        respuesta = await cliente.patch(f"{RUTA}/{ANA}", json={"activo": False})

    assert respuesta.status_code == HTTPStatus.CONFLICT
    assert respuesta.json()["errorCode"] == "AUTOEDICION_NO_PERMITIDA"


async def test_restablecer_la_clave_responde_200_con_la_clave_nueva() -> None:
    almacen = _almacen()
    async with _cliente(almacen) as cliente:
        respuesta = await cliente.post(f"{RUTA}/{ANA}/restablecer-clave")

    assert respuesta.status_code == HTTPStatus.OK
    assert len(respuesta.json()["claveInicial"]) == 20
    assert respuesta.headers["cache-control"] == "no-store"
    assert almacen.sesiones_cerradas == [ANA]


async def test_restablecer_la_clave_de_un_usuario_ajeno_o_inexistente_responde_404() -> None:
    async with _cliente(sesion=JEFE) as cliente:
        ajeno = await cliente.post(f"{RUTA}/{BRUNO}/restablecer-clave")
        invalido = await cliente.post(f"{RUTA}/xyz/restablecer-clave")

    assert ajeno.status_code == HTTPStatus.NOT_FOUND
    assert invalido.status_code == HTTPStatus.NOT_FOUND
