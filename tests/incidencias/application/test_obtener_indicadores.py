from app.enums.alcance_indicadores import AlcanceIndicadores
from app.enums.categoria_filtro import CategoriaFiltro
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.periodo_indicadores import PeriodoIndicadores
from app.enums.tarjeta_codigo import TarjetaCodigo
from app.enums.tipo_area import TipoArea
from app.incidencias.application.obtener_indicadores import ObtenerIndicadores
from app.incidencias.domain.consultas import VisibilidadDeIpress
from app.incidencias.domain.cubos_de_evolucion import DiaDeEvolucion
from app.incidencias.domain.indicadores import (
    AlcanceDeIndicadores,
    AreaDeAlcance,
    ConsultaDeIndicadores,
    FilaDistribucion,
)
from app.incidencias.domain.plazo import PlazosConfigurados
from tests.helpers.builders import un_area_de_sesion, una_sesion
from tests.helpers.indicadores_en_memoria import IndicadoresEnMemoria, un_resumen

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
ADMIN = una_sesion(roles=("ADMINISTRADOR",))
GESTOR = una_sesion(roles=("GESTOR",), area=un_area_de_sesion(id=3))


def _lector() -> IndicadoresEnMemoria:
    lector = IndicadoresEnMemoria()
    lector.filas = [
        FilaDistribucion(EstadoIncidencia.CLASIFICADO, CategoriaIncidencia.QUEJA, 3),
        FilaDistribucion(EstadoIncidencia.RESUELTO, None, 2),
    ]
    lector.dias = [DiaDeEvolucion(f"2026-10-{18 + indice}", indice, 0) for indice in range(7)]
    return lector


async def test_arma_los_indicadores_de_un_administrador_con_sus_cuatro_tarjetas() -> None:
    indicadores = await ObtenerIndicadores(_lector(), PLAZOS).execute(ADMIN, PeriodoIndicadores.SIETE_DIAS)

    assert indicadores.periodo == PeriodoIndicadores.SIETE_DIAS
    assert indicadores.generado_en == "2026-10-24T12:00:00.456Z"
    assert [(t.codigo, t.valor, t.anterior) for t in indicadores.tarjetas] == [
        (TarjetaCodigo.RECIBIDOS, 12, 9),
        (TarjetaCodigo.PENDIENTES, 4, None),
        (TarjetaCodigo.EN_GESTION, 2, None),
        (TarjetaCodigo.RESUELTOS, 5, 3),
    ]
    assert indicadores.tiempo_promedio_horas == 18.5


async def test_el_alcance_y_las_categorias_dependen_de_la_sesion() -> None:
    de_admin = await ObtenerIndicadores(_lector(), PLAZOS).execute(ADMIN, PeriodoIndicadores.SIETE_DIAS)
    de_gestor = await ObtenerIndicadores(_lector(), PLAZOS).execute(GESTOR, PeriodoIndicadores.SIETE_DIAS)

    assert (de_admin.alcance.tipo, de_admin.alcance.area) == (AlcanceIndicadores.TODO, None)
    assert de_gestor.alcance.tipo == AlcanceIndicadores.AREA
    assert [fila.categoria for fila in de_admin.por_categoria] == [CategoriaFiltro.QUEJA, CategoriaFiltro.SIN_CATEGORIA]
    assert [fila.categoria for fila in de_gestor.por_categoria] == [CategoriaFiltro.QUEJA]


async def test_los_estados_salen_completos_y_la_evolucion_diaria_no_se_agrupa_en_7_dias() -> None:
    indicadores = await ObtenerIndicadores(_lector(), PLAZOS).execute(ADMIN, PeriodoIndicadores.SIETE_DIAS)

    assert len(indicadores.por_estado) == 6
    assert len(indicadores.evolucion) == 7


async def test_en_90_dias_la_evolucion_se_agrupa_por_semana() -> None:
    lector = _lector()
    lector.dias = [DiaDeEvolucion(f"dia-{indice}", 1, 1) for indice in range(14)]

    indicadores = await ObtenerIndicadores(lector, PLAZOS).execute(ADMIN, PeriodoIndicadores.NOVENTA_DIAS)

    assert [(cubo.desde, cubo.recibidos, cubo.resueltos) for cubo in indicadores.evolucion] == [
        ("dia-0", 7, 7),
        ("dia-7", 7, 7),
    ]


async def test_pide_al_lector_los_dias_del_periodo_y_el_aviso_configurado() -> None:
    lector = _lector()

    await ObtenerIndicadores(lector, PLAZOS).execute(ADMIN, PeriodoIndicadores.TREINTA_DIAS)

    llamadas = {nombre: argumentos[1:] for nombre, argumentos in lector.llamadas}
    assert llamadas == {"resumen": (30, 48), "distribucion": (), "evolucion_diaria": (30,)}


async def test_sin_casos_resueltos_no_hay_tiempo_promedio() -> None:
    lector = _lector()
    lector.fila = un_resumen(segundos_promedio_de_resolucion=None)

    indicadores = await ObtenerIndicadores(lector, PLAZOS).execute(ADMIN, PeriodoIndicadores.SIETE_DIAS)

    assert indicadores.tiempo_promedio_horas is None


async def test_con_una_consulta_explicita_usa_su_visibilidad_y_su_alcance() -> None:
    lector = _lector()
    area = AreaDeAlcance("EESS-0001", "Centro de Salud", TipoArea.ESTABLECIMIENTO)
    consulta = ConsultaDeIndicadores(VisibilidadDeIpress(5), AlcanceDeIndicadores(AlcanceIndicadores.AREA, area))

    indicadores = await ObtenerIndicadores(lector, PLAZOS).execute(ADMIN, PeriodoIndicadores.SIETE_DIAS, consulta)

    assert indicadores.alcance.area == area
    assert all(argumentos[0] == VisibilidadDeIpress(5) for _, argumentos in lector.llamadas)
