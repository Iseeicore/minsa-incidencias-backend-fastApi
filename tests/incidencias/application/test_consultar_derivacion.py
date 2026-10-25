import pytest

from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.consultar_derivacion import ConsultarDerivacion
from app.incidencias.application.consultar_incidencia import ConsultarIncidencia
from app.incidencias.application.visibilidad import VISIBILIDAD_DE_DERIVACIONES
from app.incidencias.domain.plazo import PlazosConfigurados
from tests.helpers.builders import un_caso_consultado, una_derivacion_consultada, una_evidencia, una_sesion
from tests.helpers.derivaciones_en_memoria import DerivacionesEnMemoria
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
ADMIN = una_sesion(roles=("ADMINISTRADOR",))
CODIGO = "MINSA-2026-000001"


def _consultar(casos: IncidenciasEnMemoria, derivaciones: DerivacionesEnMemoria) -> ConsultarDerivacion:
    return ConsultarDerivacion(derivaciones, ConsultarIncidencia(casos, PLAZOS))


async def test_devuelve_el_ultimo_envio_y_el_detalle_real_del_caso_sin_acciones() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()], evidencias=[una_evidencia()])
    derivaciones = DerivacionesEnMemoria([una_derivacion_consultada()])

    detalle = await _consultar(casos, derivaciones).execute(ADMIN, CODIGO)

    assert detalle.derivacion.id == "4821"
    assert detalle.caso.resumen.codigo == CODIGO
    assert detalle.caso.resumen.acciones == ()
    assert [evidencia.id for evidencia in detalle.caso.evidencias] == ["0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"]


async def test_lee_el_caso_con_la_visibilidad_del_seguimiento_y_no_con_la_de_la_sesion() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()])
    derivaciones = DerivacionesEnMemoria([una_derivacion_consultada()])

    await _consultar(casos, derivaciones).execute(ADMIN, CODIGO)

    assert ("buscar_por_codigo", (CODIGO, VISIBILIDAD_DE_DERIVACIONES)) in casos.llamadas


async def test_un_caso_sin_envio_de_otrans_responde_404_con_el_mensaje_de_la_derivacion() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()])

    with pytest.raises(NoEncontrado, match=r"La derivación no está disponible."):
        await _consultar(casos, DerivacionesEnMemoria()).execute(ADMIN, CODIGO)

    assert casos.llamadas == []


async def test_un_envio_cuyo_caso_ya_no_se_ve_responde_404_con_el_mensaje_del_caso() -> None:
    derivaciones = DerivacionesEnMemoria([una_derivacion_consultada()])

    with pytest.raises(NoEncontrado, match=r"El caso solicitado no existe\."):
        await _consultar(IncidenciasEnMemoria(), derivaciones).execute(ADMIN, CODIGO)
