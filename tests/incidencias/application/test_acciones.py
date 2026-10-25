import pytest

from app.enums.accion_incidencia import AccionIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.resultado_resolucion import ResultadoResolucion
from app.incidencias.application.acciones import Accion, Archivar, Confirmar, Reabrir, Resolver, Tomar
from app.incidencias.domain.resultado_de_accion import ResultadoDeAccion
from tests.helpers.builders import un_caso_consultado, una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

CASO = un_caso_consultado()
SESION = una_sesion()


async def test_confirmar_marca_la_categoria_como_confirmada() -> None:
    tx = IncidenciasEnMemoria()

    await Confirmar().aplicar(tx, SESION, CASO)

    assert tx.llamadas == [("confirmar", (CASO.id,))]


async def test_tomar_pasa_el_caso_a_en_gestion() -> None:
    tx = IncidenciasEnMemoria()

    await Tomar().aplicar(tx, SESION, CASO)

    assert tx.llamadas == [("cambiar_estado", (CASO.id, EstadoIncidencia.EN_GESTION))]


async def test_resolver_registra_medidas_fundamento_y_resultado() -> None:
    tx = IncidenciasEnMemoria()

    await Resolver("Medidas tomadas", "Fundamento dado", ResultadoResolucion.ATENDIDO).aplicar(tx, SESION, CASO)

    assert tx.llamadas == [("resolver", (CASO.id, "Medidas tomadas", "Fundamento dado", ResultadoResolucion.ATENDIDO))]


async def test_archivar_registra_el_motivo_y_el_detalle() -> None:
    tx = IncidenciasEnMemoria()

    await Archivar(MotivoArchivo.NO_CORRESPONDE, "No es de este sector").aplicar(tx, SESION, CASO)

    assert tx.llamadas == [("archivar", (CASO.id, MotivoArchivo.NO_CORRESPONDE, "No es de este sector"))]


async def test_reabrir_registra_el_motivo_de_la_reapertura() -> None:
    tx = IncidenciasEnMemoria()

    await Reabrir("Llegaron nuevos datos").aplicar(tx, SESION, CASO)

    assert tx.llamadas == [("reabrir", (CASO.id, "Llegaron nuevos datos"))]


@pytest.mark.parametrize(
    ("accion", "tipo", "mensaje"),
    [
        (Confirmar(), AccionIncidencia.CONFIRMAR, "Categoría confirmada."),
        (Tomar(), AccionIncidencia.TOMAR, "Caso tomado en gestión."),
        (Resolver("a" * 10, "b" * 10, ResultadoResolucion.CERRADO), AccionIncidencia.RESOLVER, "Caso resuelto."),
        (Archivar(MotivoArchivo.DATOS_INSUFICIENTES, "c" * 10), AccionIncidencia.ARCHIVAR, "Caso archivado."),
        (Reabrir("d" * 10), AccionIncidencia.REABRIR, "Caso reabierto. Quedó en gestión."),
    ],
)
def test_si_el_caso_sale_de_la_vista_responde_el_mensaje_de_la_accion_sin_caso(
    accion: Accion, tipo: AccionIncidencia, mensaje: str
) -> None:
    assert accion.tipo == tipo
    assert accion.sin_vista("MINSA-2026-000001") == ResultadoDeAccion(mensaje, None)
