import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.filtro_corrupcion.adapters.persistence import sentencias_del_clasificador
from app.filtro_corrupcion.adapters.persistence.clasificador import SqlClasificadorUnitOfWork
from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia
from app.shared.transaction import transaction
from tests.helpers.base import consultar
from tests.helpers.casos import ACTOR_OPERADOR_USUARIO, CasoSembrado, sembrar_caso

pytestmark = pytest.mark.integration

ACTOR_PRUEBA = "sistema:clasificacion-prueba"


async def _buscar(engine: AsyncEngine, incidencia_id: str, texto: str) -> list[CandidatoCoincidencia]:
    async with SqlClasificadorUnitOfWork(engine).begin(ACTOR_PRUEBA) as transaccion:
        return await transaccion.buscar_coincidencias(incidencia_id, texto)


async def _revisado(engine: AsyncEngine, categoria: str, **opciones: str) -> CasoSembrado:
    return await sembrar_caso(engine, categoria=categoria, revision=opciones.pop("revision", "confirmada"), **opciones)  # type: ignore[arg-type]


async def test_incluye_confirmaciones_y_correcciones_con_el_codigo_de_la_categoria_humana_final(
    engine: AsyncEngine,
) -> None:
    confirmado = await _revisado(engine, "RECLAMO")
    corregido = await _revisado(engine, "RECLAMO", revision="corregida", corregida_a="QUEJA")
    actual = await sembrar_caso(engine, categoria=None)

    finales = await consultar(
        engine,
        "SELECT c.codigo, e.fue_corregida, e.apto_entrenamiento FROM ia.entrenamiento_categoria e"
        " JOIN catalogo.categoria_incidencia c ON c.id = e.categoria_final_id"
        " WHERE e.incidencia_paciente_id = ANY(CAST(:ids AS uuid[]))",
        ids=[confirmado.id, corregido.id],
    )
    desde_confirmado = await _buscar(engine, actual.id, confirmado.descripcion)
    desde_corregido = await _buscar(engine, actual.id, corregido.descripcion)

    assert ("RECLAMO", False, True) in finales
    assert ("QUEJA", True, True) in finales
    assert CandidatoCoincidencia(CategoriaIncidencia.RECLAMO, 1.0) in desde_confirmado
    assert CandidatoCoincidencia(CategoriaIncidencia.QUEJA, 1.0) in desde_corregido
    assert CandidatoCoincidencia(CategoriaIncidencia.RECLAMO, 1.0) not in desde_corregido


async def test_excluye_el_propio_caso_aunque_tenga_una_revision_y_conserve_una_coincidencia_exacta(
    engine: AsyncEngine,
) -> None:
    revisado = await _revisado(engine, "QUEJA")
    otro = await sembrar_caso(engine, categoria=None)
    exacta = CandidatoCoincidencia(CategoriaIncidencia.QUEJA, 1.0)

    assert exacta in await _buscar(engine, otro.id, revisado.descripcion)
    assert exacta not in await _buscar(engine, revisado.id, revisado.descripcion)


async def test_descarta_ejemplos_sin_revision_humana_no_aptos_por_archivo_manual_y_casos_inactivos(
    engine: AsyncEngine,
) -> None:
    sin_revision = await sembrar_caso(engine, categoria="QUEJA")
    no_apto = await _revisado(engine, "QUEJA", archivar_motivo="DATOS_INSUFICIENTES")
    inactivo = await _revisado(engine, "RECLAMO")
    async with transaction(engine, ACTOR_OPERADOR_USUARIO) as conexion:
        await conexion.execute(
            text(
                "UPDATE chatbot.incidencia_paciente SET activo = false, eliminado_en = now(), eliminado_por = :actor"
                " WHERE id = CAST(:id AS uuid)"
            ),
            {"id": inactivo.id, "actor": ACTOR_OPERADOR_USUARIO},
        )
    actual = await sembrar_caso(engine, categoria=None)

    sin_corpus = await consultar(
        engine,
        "SELECT incidencia_paciente_id FROM ia.entrenamiento_categoria WHERE incidencia_paciente_id = CAST(:id AS uuid)",
        id=sin_revision.id,
    )
    aptitud = await consultar(
        engine,
        "SELECT apto_entrenamiento FROM ia.entrenamiento_categoria WHERE incidencia_paciente_id = CAST(:id AS uuid)",
        id=no_apto.id,
    )

    assert sin_corpus == []
    assert aptitud == [(False,)]
    for caso in (sin_revision, no_apto, inactivo):
        candidatos = await _buscar(engine, actual.id, caso.descripcion)
        assert not any(candidato.similitud == 1.0 for candidato in candidatos)


async def test_un_texto_en_blanco_no_consulta_la_base(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine, categoria=None)

    assert await _buscar(engine, caso.id, "  \t\n ") == []


async def test_si_falta_una_funcion_opcional_devuelve_vacio_y_la_transaccion_sigue_sirviendo(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    caso = await sembrar_caso(engine, categoria=None)
    monkeypatch.setattr(sentencias_del_clasificador, "COINCIDENCIAS", text("SELECT public.funcion_que_no_existe()"))

    async with SqlClasificadorUnitOfWork(engine).begin(ACTOR_PRUEBA) as transaccion:
        candidatos = await transaccion.buscar_coincidencias(caso.id, "relato cualquiera")
        existe = await transaccion.area_mencionada("no-existe")

    assert (candidatos, existe) == ([], None)


async def test_si_falta_una_relacion_opcional_tambien_devuelve_vacio(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    caso = await sembrar_caso(engine, categoria=None)
    monkeypatch.setattr(sentencias_del_clasificador, "COINCIDENCIAS", text("SELECT 1 FROM ia.tabla_que_no_existe"))

    assert await _buscar(engine, caso.id, "relato cualquiera") == []


async def test_cualquier_otro_error_de_sql_se_propaga(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    caso = await sembrar_caso(engine, categoria=None)
    monkeypatch.setattr(sentencias_del_clasificador, "COINCIDENCIAS", text("SELECT columna_inexistente"))

    with pytest.raises(ProgrammingError):
        await _buscar(engine, caso.id, "relato cualquiera")
