import pytest

from app.errors.sin_permiso import SinPermiso
from app.shared.cursor import PosicionPorNombre, decode_uuid_cursor
from app.usuarios.application.listar_usuarios import ListarUsuarios
from app.usuarios.domain.pedidos import ConsultaUsuarios
from tests.helpers.builders import un_area_de_sesion, un_usuario_gestionado, una_sesion
from tests.helpers.usuarios_en_memoria import UsuariosEnMemoria

ADMIN = una_sesion(roles=("ADMINISTRADOR",))
ESTABLECIMIENTO = una_sesion(roles=("ESTABLECIMIENTO",), area=un_area_de_sesion(id=1))


def _almacen() -> UsuariosEnMemoria:
    return UsuariosEnMemoria(
        [
            un_usuario_gestionado("11111111-1111-4111-8111-111111111111", "Ana Torres", "ana@minsa.gob.pe", area_id=1),
            un_usuario_gestionado(
                "22222222-2222-4222-8222-222222222222", "Bruno Díaz", "bruno@minsa.gob.pe", area_id=2
            ),
            un_usuario_gestionado(
                "33333333-3333-4333-8333-333333333333", "Carla Ríos", "carla@minsa.gob.pe", area_id=1
            ),
        ]
    )


async def test_el_administrador_ve_a_todos_ordenados_por_nombre() -> None:
    pagina = await ListarUsuarios(_almacen()).execute(ADMIN, ConsultaUsuarios(limite=10))

    assert [usuario.nombre_completo for usuario in pagina.items] == ["Ana Torres", "Bruno Díaz", "Carla Ríos"]
    assert (pagina.siguiente, pagina.hay_mas) == (None, False)


async def test_el_administrador_puede_filtrar_por_codigo_de_area() -> None:
    pagina = await ListarUsuarios(_almacen()).execute(ADMIN, ConsultaUsuarios(limite=10, area="HOSP-02"))

    assert [usuario.nombre_completo for usuario in pagina.items] == ["Bruno Díaz"]


async def test_un_establecimiento_solo_ve_su_area_y_el_filtro_de_area_se_ignora() -> None:
    pagina = await ListarUsuarios(_almacen()).execute(ESTABLECIMIENTO, ConsultaUsuarios(limite=10, area="HOSP-02"))

    assert [usuario.nombre_completo for usuario in pagina.items] == ["Ana Torres", "Carla Ríos"]


async def test_un_establecimiento_sin_area_no_ve_a_nadie() -> None:
    sesion = una_sesion(roles=("ESTABLECIMIENTO",), area=None)

    pagina = await ListarUsuarios(_almacen()).execute(sesion, ConsultaUsuarios(limite=10))

    assert pagina.items == []


async def test_la_pagina_trae_el_cursor_del_ultimo_elemento_cuando_hay_mas() -> None:
    caso = ListarUsuarios(_almacen())

    primera = await caso.execute(ADMIN, ConsultaUsuarios(limite=2))
    posicion = decode_uuid_cursor(primera.siguiente or "")
    segunda = await caso.execute(ADMIN, ConsultaUsuarios(limite=2, despues_de=posicion))

    assert [usuario.nombre_completo for usuario in primera.items] == ["Ana Torres", "Bruno Díaz"]
    assert primera.hay_mas is True
    assert posicion == PosicionPorNombre("Bruno Díaz", "22222222-2222-4222-8222-222222222222")
    assert [usuario.nombre_completo for usuario in segunda.items] == ["Carla Ríos"]
    assert (segunda.siguiente, segunda.hay_mas) == (None, False)


async def test_el_texto_busca_por_nombre_o_correo() -> None:
    pagina = await ListarUsuarios(_almacen()).execute(ADMIN, ConsultaUsuarios(limite=10, texto="carla"))

    assert [usuario.nombre_completo for usuario in pagina.items] == ["Carla Ríos"]


@pytest.mark.parametrize("roles", [("GESTOR",), ("OTRANS",), ()])
async def test_quien_no_gestiona_usuarios_recibe_403(roles: tuple[str, ...]) -> None:
    with pytest.raises(SinPermiso):
        await ListarUsuarios(_almacen()).execute(una_sesion(roles=roles), ConsultaUsuarios(limite=10))
