import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_api import EstadoApi
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.resultado_resolucion import ResultadoResolucion
from app.errors.conflicto import Conflicto
from app.errors.no_encontrado import NoEncontrado
from app.errors.no_procesable import NoProcesable
from app.errors.sin_permiso import SinPermiso
from app.incidencias.adapters.persistence.escritura import SqlIncidenciaUnitOfWork
from app.incidencias.adapters.persistence.repository import SqlIncidenciaReader
from app.incidencias.application.acciones import Accion, Archivar, Confirmar, Reabrir, Resolver, Tomar
from app.incidencias.application.acciones_de_derivacion import Corregir, Derivar
from app.incidencias.application.ejecutar_accion import EjecutarAccion
from app.incidencias.domain.plazo import PlazosConfigurados
from app.incidencias.domain.resultado_de_accion import CasoEnviadoAOtrans, ResultadoDeAccion
from app.shared.sesion import SesionActual
from tests.helpers.base import consultar
from tests.helpers.builders import un_area_de_sesion, una_sesion
from tests.helpers.casos import EstablecimientoSembrado, sembrar_caso, sembrar_establecimiento

pytestmark = pytest.mark.integration

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
TEXTO = "Texto de al menos diez caracteres"
ADMIN = una_sesion(correo="admin@minsa.gob.pe", roles=("ADMINISTRADOR",))


def _gestor(sitio: EstablecimientoSembrado) -> SesionActual:
    return una_sesion(correo="gestor@minsa.gob.pe", roles=("GESTOR",), area=un_area_de_sesion(id=sitio.area_id))


def _ejecutor(engine: AsyncEngine) -> EjecutarAccion:
    return EjecutarAccion(SqlIncidenciaUnitOfWork(engine), SqlIncidenciaReader(engine), PLAZOS)


async def _ejecutar(
    engine: AsyncEngine, sesion: SesionActual, codigo: str, accion: Accion
) -> ResultadoDeAccion | CasoEnviadoAOtrans:
    return await _ejecutor(engine).execute(sesion, codigo, accion)


async def _detalle(engine: AsyncEngine, sesion: SesionActual, codigo: str, accion: Accion) -> ResultadoDeAccion:
    resultado = await _ejecutar(engine, sesion, codigo, accion)
    assert isinstance(resultado, ResultadoDeAccion)
    assert resultado.caso is not None
    return resultado


async def _establecimiento(engine: AsyncEngine, identificador: int = 101) -> EstablecimientoSembrado:
    return await sembrar_establecimiento(engine, identificador)


async def test_confirmar_deja_el_caso_revisado_y_lo_registra_en_el_historial(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine)

    resultado = await _detalle(engine, ADMIN, caso.codigo, Confirmar())

    assert resultado.mensaje == "Categoría confirmada."
    assert resultado.caso is not None
    assert resultado.caso.resumen.revisado_por_humano is True
    assert resultado.caso.historial[-1].titulo == "Categoría confirmada"


async def test_corregir_cambia_la_categoria_y_la_marca_como_corregida(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine)

    resultado = await _detalle(engine, ADMIN, caso.codigo, Corregir(CategoriaIncidencia.QUEJA))

    assert resultado.caso is not None
    assert resultado.caso.resumen.categoria == "queja"
    assert resultado.caso.resumen.corregida is True


async def test_corregir_a_denuncia_saca_el_caso_de_la_vista_del_establecimiento(engine: AsyncEngine) -> None:
    sitio = await _establecimiento(engine)
    caso = await sembrar_caso(engine, establecimiento=sitio)
    jefe = una_sesion(correo="jefe@minsa.gob.pe", roles=("ESTABLECIMIENTO",), area=un_area_de_sesion(id=sitio.area_id))

    resultado = await _ejecutar(engine, jefe, caso.codigo, Corregir(CategoriaIncidencia.DENUNCIA_CORRUPCION))

    assert resultado == CasoEnviadoAOtrans(caso.codigo)
    filas = await consultar(
        engine,
        "SELECT k.codigo, (SELECT t.codigo FROM catalogo.area a JOIN catalogo.tipo_area t ON t.id = a.tipo_area_id"
        " WHERE a.id = i.area_destino_id) FROM chatbot.incidencia_paciente i"
        " JOIN catalogo.categoria_incidencia k ON k.id = i.categoria_id WHERE i.codigo = :codigo",
        codigo=caso.codigo,
    )
    assert filas == [("DENUNCIA_CORRUPCION", "OTRANS")]


async def test_tomar_pasa_un_caso_revisado_a_en_gestion(engine: AsyncEngine) -> None:
    sitio = await _establecimiento(engine)
    caso = await sembrar_caso(engine, establecimiento=sitio, revision="confirmada")

    resultado = await _detalle(engine, _gestor(sitio), caso.codigo, Tomar())

    assert resultado.caso is not None
    assert resultado.caso.resumen.estado == EstadoApi.EN_GESTION


async def test_derivar_envia_el_caso_revisado_al_area_del_establecimiento(engine: AsyncEngine) -> None:
    sitio = await _establecimiento(engine)
    caso = await sembrar_caso(engine, establecimiento=sitio, revision="confirmada")

    resultado = await _detalle(engine, ADMIN, caso.codigo, Derivar(TEXTO, sitio.area_codigo))

    assert resultado.mensaje == "Caso derivado al área."
    assert resultado.caso is not None
    assert resultado.caso.resumen.estado == EstadoApi.DERIVADO
    assert resultado.caso.resumen.area is not None
    assert resultado.caso.resumen.area.codigo == sitio.area_codigo
    assert resultado.caso.descripcion_derivacion == TEXTO


async def test_derivar_a_un_area_distinta_de_la_vinculada_responde_422(engine: AsyncEngine) -> None:
    sitio = await _establecimiento(engine, 101)
    otro = await _establecimiento(engine, 102)
    caso = await sembrar_caso(engine, establecimiento=sitio, revision="confirmada")

    with pytest.raises(NoProcesable, match="Solo se puede derivar al establecimiento vinculado"):
        await _ejecutar(engine, ADMIN, caso.codigo, Derivar(TEXTO, otro.area_codigo))


async def test_resolver_registra_la_resolucion_y_deja_el_caso_resuelto(engine: AsyncEngine) -> None:
    sitio = await _establecimiento(engine)
    caso = await sembrar_caso(engine, establecimiento=sitio, estado="EN_GESTION")

    resultado = await _detalle(
        engine, _gestor(sitio), caso.codigo, Resolver(TEXTO, f"{TEXTO} y más", ResultadoResolucion.ATENDIDO)
    )

    assert resultado.caso is not None
    assert resultado.caso.resumen.estado == EstadoApi.RESUELTO
    assert resultado.caso.resolucion is not None
    assert (resultado.caso.resolucion.medidas_tomadas, resultado.caso.resolucion.resultado) == (
        TEXTO,
        ResultadoResolucion.ATENDIDO,
    )


async def test_archivar_deja_el_caso_archivado_con_su_motivo_y_detalle(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine)

    resultado = await _detalle(engine, ADMIN, caso.codigo, Archivar(MotivoArchivo.DATOS_INSUFICIENTES, TEXTO))

    assert resultado.caso is not None
    assert resultado.caso.resumen.estado == EstadoApi.ARCHIVADO
    assert resultado.caso.archivo is not None
    assert (resultado.caso.archivo.motivo, resultado.caso.archivo.detalle) == (MotivoArchivo.DATOS_INSUFICIENTES, TEXTO)


async def test_reabrir_devuelve_un_archivado_a_en_gestion_con_el_motivo(engine: AsyncEngine) -> None:
    sitio = await _establecimiento(engine)
    caso = await sembrar_caso(engine, establecimiento=sitio, archivar_motivo="DATOS_INSUFICIENTES")

    resultado = await _detalle(engine, ADMIN, caso.codigo, Reabrir(TEXTO))

    assert resultado.caso is not None
    assert resultado.caso.resumen.estado == EstadoApi.EN_GESTION
    assert resultado.caso.reapertura is not None
    assert resultado.caso.reapertura.motivo == TEXTO


async def test_una_accion_que_el_estado_no_permite_responde_403_y_no_cambia_nada(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine)

    with pytest.raises(SinPermiso, match=r"No puedes resolver este caso\."):
        await _ejecutar(engine, ADMIN, caso.codigo, Resolver(TEXTO, TEXTO, ResultadoResolucion.ATENDIDO))

    estados = await consultar(
        engine,
        "SELECT e.codigo FROM chatbot.incidencia_paciente i JOIN catalogo.estado_incidencia e"
        " ON e.id = i.estado_incidencia_id WHERE i.codigo = :codigo",
        codigo=caso.codigo,
    )
    assert estados == [("CLASIFICADO",)]


async def test_un_caso_que_no_existe_responde_404(engine: AsyncEngine) -> None:
    with pytest.raises(NoEncontrado):
        await _ejecutar(engine, ADMIN, "MINSA-2026-999999", Confirmar())


async def test_la_base_rechaza_reabrir_un_caso_archivado_por_vigencia_y_responde_409(engine: AsyncEngine) -> None:
    caso = await sembrar_caso(engine, estado="ARCHIVADO")

    with pytest.raises(Conflicto, match="Este caso no se puede reabrir"):
        await _ejecutar(engine, ADMIN, caso.codigo, Reabrir(TEXTO))


async def test_dos_peticiones_a_la_vez_sobre_el_mismo_caso_se_serializan_y_solo_una_gana(engine: AsyncEngine) -> None:
    sitio = await _establecimiento(engine)
    caso = await sembrar_caso(engine, establecimiento=sitio, revision="confirmada")

    resultados = await asyncio.gather(
        _ejecutar(engine, _gestor(sitio), caso.codigo, Tomar()),
        _ejecutar(engine, _gestor(sitio), caso.codigo, Tomar()),
        return_exceptions=True,
    )

    exitos = [r for r in resultados if isinstance(r, ResultadoDeAccion)]
    rechazos = [r for r in resultados if isinstance(r, SinPermiso)]
    assert (len(exitos), len(rechazos)) == (1, 1)
