import pytest

from app.enums.alcance_indicadores import AlcanceIndicadores
from app.enums.categoria_filtro import CategoriaFiltro
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_api import EstadoApi
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.tarjeta_codigo import TarjetaCodigo
from app.enums.tipo_area import TipoArea
from app.incidencias.application.armar_indicadores import (
    alcance_de,
    cantidades_por_categoria,
    cantidades_por_estado,
    horas_promedio,
    resumir_ipress,
    sumar_por_categoria,
    sumar_por_estado,
    tarjeta_de,
)
from app.incidencias.domain.indicadores import FilaDistribucion
from tests.helpers.builders import un_area_de_sesion, una_sesion
from tests.helpers.indicadores_en_memoria import un_resumen


@pytest.mark.parametrize(
    ("codigo", "valor", "anterior"),
    [
        (TarjetaCodigo.RECIBIDOS, 12, 9),
        (TarjetaCodigo.PENDIENTES, 4, None),
        (TarjetaCodigo.EN_GESTION, 2, None),
        (TarjetaCodigo.POR_VENCER, 1, None),
        (TarjetaCodigo.VENCIDOS, 1, None),
        (TarjetaCodigo.RESUELTOS, 5, 3),
        (TarjetaCodigo.SIN_CLASIFICAR, 2, None),
        (TarjetaCodigo.POR_REVISAR, 3, None),
        (TarjetaCodigo.SIN_TOMAR, 1, None),
        (TarjetaCodigo.CORREGIDAS_A_CORRUPCION, 1, 0),
    ],
)
def test_cada_tarjeta_toma_su_valor_y_solo_algunas_traen_el_periodo_anterior(
    codigo: TarjetaCodigo, valor: int, anterior: int | None
) -> None:
    tarjeta = tarjeta_de(codigo, un_resumen())

    assert (tarjeta.codigo, tarjeta.valor, tarjeta.anterior) == (codigo, valor, anterior)


def test_quien_cuenta_todas_las_areas_tiene_alcance_total_sin_area() -> None:
    alcance = alcance_de(una_sesion(roles=("ADMINISTRADOR",)))

    assert (alcance.tipo, alcance.area) == (AlcanceIndicadores.TODO, None)


def test_el_resto_tiene_alcance_de_su_area() -> None:
    sesion = una_sesion(roles=("GESTOR",), area=un_area_de_sesion(id=3))

    alcance = alcance_de(sesion)

    assert alcance.tipo == AlcanceIndicadores.AREA
    assert alcance.area is not None
    assert (alcance.area.codigo, alcance.area.nombre, alcance.area.tipo) == (
        "HOSP-01",
        "Hospital Uno",
        TipoArea.ESTABLECIMIENTO,
    )


def test_un_usuario_sin_area_tiene_alcance_de_area_vacia() -> None:
    alcance = alcance_de(una_sesion(roles=("GESTOR",)))

    assert (alcance.tipo, alcance.area) == (AlcanceIndicadores.AREA, None)


def _distribucion() -> list[FilaDistribucion]:
    return [
        FilaDistribucion(EstadoIncidencia.CLASIFICADO, CategoriaIncidencia.QUEJA, 3),
        FilaDistribucion(EstadoIncidencia.CLASIFICADO, CategoriaIncidencia.RECLAMO, 2),
        FilaDistribucion(EstadoIncidencia.EN_GESTION, CategoriaIncidencia.QUEJA, 1),
        FilaDistribucion(EstadoIncidencia.RESUELTO, None, 4),
        FilaDistribucion(EstadoIncidencia.ARCHIVADO, CategoriaIncidencia.OTRO, 5),
    ]


def test_las_sumas_agrupan_por_estado_y_por_categoria() -> None:
    assert sumar_por_estado(_distribucion()) == {
        EstadoIncidencia.CLASIFICADO: 5,
        EstadoIncidencia.EN_GESTION: 1,
        EstadoIncidencia.RESUELTO: 4,
        EstadoIncidencia.ARCHIVADO: 5,
    }
    assert sumar_por_categoria(_distribucion()) == {
        CategoriaIncidencia.QUEJA: 4,
        CategoriaIncidencia.RECLAMO: 2,
        None: 4,
        CategoriaIncidencia.OTRO: 5,
    }


def test_las_categorias_salen_en_el_orden_del_contrato_con_o_sin_la_de_sin_categoria() -> None:
    cantidades = sumar_por_categoria(_distribucion())

    con = cantidades_por_categoria(cantidades, con_sin_categoria=True)
    sin = cantidades_por_categoria(cantidades, con_sin_categoria=False)

    assert [(fila.categoria, fila.cantidad) for fila in con] == [
        (CategoriaFiltro.DENUNCIA_CORRUPCION, 0),
        (CategoriaFiltro.QUEJA, 4),
        (CategoriaFiltro.RECLAMO, 2),
        (CategoriaFiltro.OTRO, 5),
        (CategoriaFiltro.SIN_CATEGORIA, 4),
    ]
    assert len(sin) == 4


def test_los_estados_salen_completos_y_en_el_idioma_del_contrato() -> None:
    estados = cantidades_por_estado({EstadoIncidencia.EN_GESTION: 2})

    assert [(fila.estado, fila.cantidad) for fila in estados] == [
        (EstadoApi.REGISTRADO, 0),
        (EstadoApi.CLASIFICADO, 0),
        (EstadoApi.DERIVADO, 0),
        (EstadoApi.EN_GESTION, 2),
        (EstadoApi.RESUELTO, 0),
        (EstadoApi.ARCHIVADO, 0),
    ]


@pytest.mark.parametrize(
    ("segundos", "esperado"),
    [(None, None), (0.0, 0.0), (66_600.0, 18.5), (3_600.0, 1.0), (5_400.0, 1.5), (4_050.0, 1.1), (4_000.0, 1.1)],
)
def test_las_horas_promedio_se_redondean_a_un_decimal_como_math_round(
    segundos: float | None, esperado: float | None
) -> None:
    assert horas_promedio(segundos) == esperado


def test_el_resumen_de_una_ipress_cuenta_abiertos_y_siempre_incluye_las_cinco_categorias() -> None:
    resumen = resumir_ipress(_distribucion())

    assert (resumen.total, resumen.abiertos, resumen.en_gestion, resumen.resueltos, resumen.archivados) == (
        15,
        6,
        1,
        4,
        5,
    )
    assert [fila.categoria for fila in resumen.por_categoria][-1] == CategoriaFiltro.SIN_CATEGORIA
    assert len(resumen.por_categoria) == 5


def test_el_resumen_de_una_ipress_sin_casos_es_todo_ceros() -> None:
    resumen = resumir_ipress([])

    assert (resumen.total, resumen.abiertos) == (0, 0)
    assert {fila.cantidad for fila in resumen.por_categoria} == {0}
