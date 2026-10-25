import pytest

from app.enums.alcance_indicadores import AlcanceIndicadores
from app.enums.categoria_filtro import CategoriaFiltro
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.periodo_indicadores import PeriodoIndicadores
from app.enums.tipo_area import TipoArea
from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.consulta_de_ipress import (
    ConsultarIncidenciaDeIpress,
    ContarIncidenciasDeIpress,
    ContenidoDeEvidenciaDeIpress,
    ListarIncidenciasDeIpress,
    ObtenerIndicadoresDeIpress,
    ObtenerResumenDeIpress,
)
from app.incidencias.application.consultar_incidencia import ConsultarIncidencia
from app.incidencias.application.contar_incidencias import ContarIncidencias
from app.incidencias.application.contenido_de_evidencia import ContenidoDeEvidencia
from app.incidencias.application.listar_incidencias import ListarIncidencias
from app.incidencias.application.obtener_indicadores import ObtenerIndicadores
from app.incidencias.domain.consultas import ConsultaListado, FiltrosConsulta, VisibilidadDeIpress
from app.incidencias.domain.indicadores import FilaDistribucion
from app.incidencias.domain.ipress import IpressConsultada
from app.incidencias.domain.plazo import PlazosConfigurados
from tests.helpers.builders import un_caso_consultado, una_evidencia, una_sesion
from tests.helpers.casos import IMAGEN_PNG
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria
from tests.helpers.indicadores_en_memoria import IndicadoresEnMemoria, IpressEnMemoria

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
OTRANS = una_sesion(roles=("OTRANS",))
CODIGO = "MINSA-2026-000001"
RENIPRESS = "1234"
VISIBLE = VisibilidadDeIpress(establecimiento_id=7)


def _ipress() -> IpressEnMemoria:
    return IpressEnMemoria({RENIPRESS: IpressConsultada(7, "EESS-0001", "Centro de Salud")})


async def test_el_resumen_cuenta_con_la_visibilidad_del_establecimiento() -> None:
    indicadores = IndicadoresEnMemoria()
    indicadores.filas = [FilaDistribucion(EstadoIncidencia.EN_GESTION, None, 2)]

    resumen = await ObtenerResumenDeIpress(_ipress(), indicadores).execute(RENIPRESS)

    assert (resumen.total, resumen.en_gestion) == (2, 2)
    assert resumen.por_categoria[-1].categoria == CategoriaFiltro.SIN_CATEGORIA
    assert indicadores.llamadas == [("distribucion", (VISIBLE,))]


async def test_los_indicadores_llevan_el_area_del_establecimiento_como_alcance() -> None:
    lector = IndicadoresEnMemoria()
    obtener = ObtenerIndicadores(lector, PLAZOS)

    indicadores = await ObtenerIndicadoresDeIpress(_ipress(), obtener).execute(
        OTRANS, RENIPRESS, PeriodoIndicadores.TREINTA_DIAS
    )

    assert indicadores.alcance.tipo == AlcanceIndicadores.AREA
    assert indicadores.alcance.area is not None
    assert (indicadores.alcance.area.codigo, indicadores.alcance.area.tipo) == ("EESS-0001", TipoArea.ESTABLECIMIENTO)
    assert all(argumentos[0] == VISIBLE for _, argumentos in lector.llamadas)


async def test_el_listado_ignora_el_filtro_de_establecimiento_y_no_trae_acciones() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()])
    consulta = ConsultaListado(limite=10, filtros=FiltrosConsulta(establecimiento="999", texto="goteras"))

    pagina = await ListarIncidenciasDeIpress(_ipress(), ListarIncidencias(casos, PLAZOS)).execute(
        OTRANS, RENIPRESS, consulta
    )

    nombre, argumentos = casos.llamadas[0]
    assert nombre == "listar"
    assert argumentos[0] == VISIBLE
    assert (argumentos[1].establecimiento, argumentos[1].texto) == (None, "goteras")
    assert pagina.items[0].acciones == ()


async def test_los_conteos_ignoran_el_filtro_de_establecimiento() -> None:
    casos = IncidenciasEnMemoria()

    await ContarIncidenciasDeIpress(_ipress(), ContarIncidencias(casos, PLAZOS)).execute(
        OTRANS, RENIPRESS, FiltrosConsulta(establecimiento="999")
    )

    assert all(argumentos[0] == VISIBLE and argumentos[1].establecimiento is None for _, argumentos in casos.llamadas)


async def test_el_detalle_del_caso_sale_sin_acciones_y_con_la_visibilidad_del_establecimiento() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()], evidencias=[una_evidencia()])

    detalle = await ConsultarIncidenciaDeIpress(_ipress(), ConsultarIncidencia(casos, PLAZOS)).execute(
        OTRANS, RENIPRESS, CODIGO
    )

    assert detalle.resumen.acciones == ()
    assert ("buscar_por_codigo", (CODIGO, VISIBLE)) in casos.llamadas


async def test_la_evidencia_se_lee_con_la_visibilidad_del_establecimiento() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()], rutas={"e1": IMAGEN_PNG})

    imagen = await ContenidoDeEvidenciaDeIpress(_ipress(), ContenidoDeEvidencia(casos)).execute(
        OTRANS, RENIPRESS, CODIGO, "e1"
    )

    assert imagen.tipo == "image/png"
    assert ("buscar_por_codigo", (CODIGO, VISIBLE)) in casos.llamadas


async def test_una_ipress_que_no_existe_responde_404_con_el_mensaje_del_establecimiento() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()])
    sin_ipress = IpressEnMemoria()

    with pytest.raises(NoEncontrado, match=r"El establecimiento no está disponible\."):
        await ConsultarIncidenciaDeIpress(sin_ipress, ConsultarIncidencia(casos, PLAZOS)).execute(OTRANS, "9", CODIGO)

    assert casos.llamadas == []


async def test_todas_las_consultas_fallan_igual_con_una_ipress_desconocida() -> None:
    casos = IncidenciasEnMemoria()
    vacia = IpressEnMemoria()
    consultas = [
        ObtenerResumenDeIpress(vacia, IndicadoresEnMemoria()).execute("9"),
        ObtenerIndicadoresDeIpress(vacia, ObtenerIndicadores(IndicadoresEnMemoria(), PLAZOS)).execute(
            OTRANS, "9", PeriodoIndicadores.SIETE_DIAS
        ),
        ListarIncidenciasDeIpress(vacia, ListarIncidencias(casos, PLAZOS)).execute(
            OTRANS, "9", ConsultaListado(limite=1)
        ),
        ContarIncidenciasDeIpress(vacia, ContarIncidencias(casos, PLAZOS)).execute(OTRANS, "9", FiltrosConsulta()),
        ContenidoDeEvidenciaDeIpress(vacia, ContenidoDeEvidencia(casos)).execute(OTRANS, "9", CODIGO, "e1"),
    ]

    for consulta in consultas:
        with pytest.raises(NoEncontrado, match=r"El establecimiento no está disponible\."):
            await consulta
