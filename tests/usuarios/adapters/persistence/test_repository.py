import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.enums.error_code import ErrorCode
from app.enums.rol_codigo import RolCodigo
from app.errors.conflicto import Conflicto
from app.errors.correo_repetido import CorreoRepetido
from app.errors.no_procesable import NoProcesable
from app.shared.cursor import PosicionPorNombre
from app.usuarios.adapters.persistence.repository import SqlUsuarioReader, SqlUsuarioUnitOfWork
from app.usuarios.domain.pedidos import FiltrosDeUsuarios, NuevoUsuarioFila, RestriccionDeArea
from tests.helpers.base import (
    ACTOR_DE_PRUEBA,
    HUELLA_DE_PRUEBA,
    TIPO_OTRANS,
    consultar,
    sembrar_area,
    sembrar_usuario,
)

pytestmark = pytest.mark.integration


async def _escenario(engine: AsyncEngine) -> dict[str, str]:
    await sembrar_area(engine, 10, "HOSP-01", "Hospital Uno")
    await sembrar_area(engine, 11, "HOSP-02", "Hospital Dos")
    return {
        "ana": await sembrar_usuario(engine, "ana@minsa.gob.pe", "GESTOR", 10, nombre="Ana Torres"),
        "bruno": await sembrar_usuario(engine, "bruno@minsa.gob.pe", "ESTABLECIMIENTO", 11, nombre="Bruno Díaz"),
        "admin": await sembrar_usuario(engine, "admin@minsa.gob.pe", "ADMINISTRADOR", None, nombre="Carla Admin"),
    }


async def test_lista_ordenada_por_nombre_con_rol_y_area(engine: AsyncEngine) -> None:
    ids = await _escenario(engine)

    usuarios = await SqlUsuarioReader(engine).listar(FiltrosDeUsuarios(), 10, None)

    assert [usuario.id for usuario in usuarios] == [ids["ana"], ids["bruno"], ids["admin"]]
    assert (usuarios[0].rol, usuarios[0].area_codigo, usuarios[0].area_nombre) == ("GESTOR", "HOSP-01", "Hospital Uno")
    assert (usuarios[2].rol, usuarios[2].area_id, usuarios[2].area_codigo) == ("ADMINISTRADOR", None, None)


async def test_el_cursor_continua_despues_de_la_posicion_dada(engine: AsyncEngine) -> None:
    ids = await _escenario(engine)

    usuarios = await SqlUsuarioReader(engine).listar(
        FiltrosDeUsuarios(), 10, PosicionPorNombre("Ana Torres", ids["ana"])
    )

    assert [usuario.id for usuario in usuarios] == [ids["bruno"], ids["admin"]]


async def test_el_limite_corta_la_pagina(engine: AsyncEngine) -> None:
    await _escenario(engine)

    assert len(await SqlUsuarioReader(engine).listar(FiltrosDeUsuarios(), 2, None)) == 2


async def test_busca_por_nombre_sin_tildes_ni_mayusculas_y_por_correo(engine: AsyncEngine) -> None:
    ids = await _escenario(engine)
    lector = SqlUsuarioReader(engine)

    por_nombre = await lector.listar(FiltrosDeUsuarios(texto="BRUNO diaz"), 10, None)
    por_correo = await lector.listar(FiltrosDeUsuarios(texto="admin@"), 10, None)

    assert [usuario.id for usuario in por_nombre] == [ids["bruno"]]
    assert [usuario.id for usuario in por_correo] == [ids["admin"]]


async def test_un_comodin_escrito_por_la_persona_no_coincide_con_todo(engine: AsyncEngine) -> None:
    await _escenario(engine)

    assert await SqlUsuarioReader(engine).listar(FiltrosDeUsuarios(texto="%\\%%"), 10, None) == []


async def test_filtra_por_codigo_de_area_y_restringe_a_un_area(engine: AsyncEngine) -> None:
    ids = await _escenario(engine)
    lector = SqlUsuarioReader(engine)

    por_codigo = await lector.listar(FiltrosDeUsuarios(area_codigo="HOSP-02"), 10, None)
    restringida = await lector.listar(FiltrosDeUsuarios(restriccion_de_area=RestriccionDeArea(10)), 10, None)
    sin_area = await lector.listar(FiltrosDeUsuarios(restriccion_de_area=RestriccionDeArea(None)), 10, None)

    assert [usuario.id for usuario in por_codigo] == [ids["bruno"]]
    assert [usuario.id for usuario in restringida] == [ids["ana"]]
    assert sin_area == []


async def test_crear_asigna_rol_y_lo_deja_leer(engine: AsyncEngine) -> None:
    await _escenario(engine)
    unidad = SqlUsuarioUnitOfWork(engine)

    async with unidad.begin(ACTOR_DE_PRUEBA) as tx:
        usuario_id = await tx.crear(NuevoUsuarioFila("Dora Nueva", "dora@minsa.gob.pe", HUELLA_DE_PRUEBA, 10))
        await tx.asignar_rol(usuario_id, RolCodigo.GESTOR)
        creado = await tx.buscar_por_id(usuario_id, None)

    assert creado is not None
    assert (creado.nombre_completo, creado.rol, creado.area_codigo, creado.activo) == (
        "Dora Nueva",
        "GESTOR",
        "HOSP-01",
        True,
    )


async def test_un_correo_repetido_se_reconoce(engine: AsyncEngine) -> None:
    await _escenario(engine)

    with pytest.raises(CorreoRepetido):
        async with SqlUsuarioUnitOfWork(engine).begin(ACTOR_DE_PRUEBA) as tx:
            await tx.crear(NuevoUsuarioFila("Otra Ana", "ana@minsa.gob.pe", HUELLA_DE_PRUEBA, 10))


async def test_un_error_deshace_toda_la_transaccion(engine: AsyncEngine) -> None:
    await _escenario(engine)
    mensaje = "falla a mitad"

    async def intentar() -> None:
        async with SqlUsuarioUnitOfWork(engine).begin(ACTOR_DE_PRUEBA) as tx:
            await tx.crear(NuevoUsuarioFila("Eva Temporal", "eva@minsa.gob.pe", HUELLA_DE_PRUEBA, 10))
            raise RuntimeError(mensaje)

    with pytest.raises(RuntimeError, match=mensaje):
        await intentar()

    assert await consultar(engine, "SELECT 1 FROM gestion.usuario_interno WHERE correo = 'eva@minsa.gob.pe'") == []


async def test_el_cuarto_usuario_activo_de_un_establecimiento_se_rechaza_con_su_codigo(engine: AsyncEngine) -> None:
    await _escenario(engine)
    await sembrar_usuario(engine, "u2@minsa.gob.pe", "GESTOR", 10)
    await sembrar_usuario(engine, "u3@minsa.gob.pe", "GESTOR", 10)

    with pytest.raises(Conflicto) as capturado:
        await sembrar_usuario(engine, "u4@minsa.gob.pe", "GESTOR", 10)

    assert capturado.value.error_code is ErrorCode.LIMITE_USUARIOS_ESTABLECIMIENTO


async def test_un_rol_que_no_corresponde_al_tipo_de_area_es_no_procesable(engine: AsyncEngine) -> None:
    await sembrar_area(engine, 20, "OTR-01", "Oficina", TIPO_OTRANS)

    with pytest.raises(NoProcesable):
        await sembrar_usuario(engine, "mal@minsa.gob.pe", "GESTOR", 20)


async def test_buscar_por_id_respeta_la_restriccion_de_area_y_el_bloqueo(engine: AsyncEngine) -> None:
    ids = await _escenario(engine)

    async with SqlUsuarioUnitOfWork(engine).begin(ACTOR_DE_PRUEBA) as tx:
        propio = await tx.buscar_por_id(ids["ana"], RestriccionDeArea(10), bloquear=True)
        ajeno = await tx.buscar_por_id(ids["ana"], RestriccionDeArea(11))
        inexistente = await tx.buscar_por_id("0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69", None)

    assert propio is not None
    assert ajeno is None
    assert inexistente is None


async def test_area_activa_distingue_codigos_y_areas_desactivadas(engine: AsyncEngine) -> None:
    await _escenario(engine)

    async with SqlUsuarioUnitOfWork(engine).begin(ACTOR_DE_PRUEBA) as tx:
        assert await tx.area_activa("HOSP-01") == 10
        assert await tx.area_activa("NO-EXISTE") is None


async def test_los_cambios_de_nombre_area_rol_vigencia_y_clave_se_guardan(engine: AsyncEngine) -> None:
    ids = await _escenario(engine)

    async with SqlUsuarioUnitOfWork(engine).begin(ACTOR_DE_PRUEBA) as tx:
        await tx.cambiar_nombre(ids["ana"], "Ana María Torres")
        await tx.quitar_roles(ids["ana"])
        await tx.asignar_rol(ids["ana"], RolCodigo.ESTABLECIMIENTO)
        await tx.cambiar_area(ids["ana"], 11)
        await tx.cambiar_clave(ids["ana"], HUELLA_DE_PRUEBA)
        await tx.cambiar_vigencia(ids["ana"], activo=False, actor="usuario:admin@minsa.gob.pe")
        cambiado = await tx.buscar_por_id(ids["ana"], None)

    assert cambiado is not None
    assert (cambiado.nombre_completo, cambiado.rol, cambiado.area_codigo, cambiado.activo) == (
        "Ana María Torres",
        "ESTABLECIMIENTO",
        "HOSP-02",
        False,
    )
    filas = await consultar(
        engine,
        "SELECT eliminado_por FROM gestion.usuario_interno WHERE id = CAST(:id AS uuid)",
        id=ids["ana"],
    )
    assert filas == [("usuario:admin@minsa.gob.pe",)]


async def test_reactivar_limpia_la_marca_de_baja(engine: AsyncEngine) -> None:
    await sembrar_area(engine, 10, "HOSP-01", "Hospital Uno")
    usuario_id = await sembrar_usuario(engine, "baja@minsa.gob.pe", "GESTOR", 10, activo=False)

    async with SqlUsuarioUnitOfWork(engine).begin(ACTOR_DE_PRUEBA) as tx:
        await tx.cambiar_vigencia(usuario_id, activo=True, actor=ACTOR_DE_PRUEBA)

    filas = await consultar(
        engine,
        "SELECT activo, eliminado_en, eliminado_por FROM gestion.usuario_interno WHERE id = CAST(:id AS uuid)",
        id=usuario_id,
    )
    assert filas == [(True, None, None)]


async def test_cerrar_sesiones_revoca_las_abiertas_del_usuario(engine: AsyncEngine) -> None:
    ids = await _escenario(engine)
    async with SqlUsuarioUnitOfWork(engine).begin(ACTOR_DE_PRUEBA) as tx:
        await tx.cerrar_sesiones(ids["ana"])

    filas = await consultar(
        engine,
        "SELECT count(*) FROM gestion.sesion_usuario"
        " WHERE usuario_interno_id = CAST(:id AS uuid) AND revocada_en IS NULL",
        id=ids["ana"],
    )
    assert filas == [(0,)]
