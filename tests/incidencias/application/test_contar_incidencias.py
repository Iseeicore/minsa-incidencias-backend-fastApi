from app.enums.estado_api import EstadoApi
from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.application.contar_incidencias import ContarIncidencias
from app.incidencias.domain.consultas import FiltrosConsulta
from app.incidencias.domain.plazo import PlazosConfigurados
from tests.helpers.builders import una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
ADMIN = una_sesion(roles=("ADMINISTRADOR",))


async def test_sin_pestana_el_total_es_igual_a_todos_y_no_se_pide_el_conteo_acotado() -> None:
    lector = IncidenciasEnMemoria()
    lector.por_estado = {EstadoIncidencia.CLASIFICADO: 3, EstadoIncidencia.EN_GESTION: 2}

    conteos = await ContarIncidencias(lector, PLAZOS).execute(ADMIN, FiltrosConsulta())

    assert (conteos.todos.cantidad, conteos.total.cantidad) == (5, 5)
    assert conteos.por_estado[EstadoApi.CLASIFICADO].cantidad == 3
    assert conteos.por_estado[EstadoApi.RESUELTO].cantidad == 0
    assert set(conteos.por_estado) == set(EstadoApi)
    assert [nombre for nombre, _ in lector.llamadas] == ["contar_por_estado"]


async def test_con_una_pestana_el_total_sale_del_conteo_acotado_y_los_estados_ignoran_la_pestana() -> None:
    lector = IncidenciasEnMemoria()
    lector.por_estado = {EstadoIncidencia.CLASIFICADO: 3, EstadoIncidencia.EN_GESTION: 2}
    lector.acotado = 3

    conteos = await ContarIncidencias(lector, PLAZOS).execute(ADMIN, FiltrosConsulta(estado=EstadoApi.CLASIFICADO))

    assert (conteos.todos.cantidad, conteos.total.cantidad) == (5, 3)
    filtros_de_estados = next(argumentos[1] for nombre, argumentos in lector.llamadas if nombre == "contar_por_estado")
    assert filtros_de_estados.estado is None


async def test_los_conteos_se_acotan_al_tope_y_avisan_que_hay_mas() -> None:
    lector = IncidenciasEnMemoria()
    lector.por_estado = {EstadoIncidencia.CLASIFICADO: 15, EstadoIncidencia.EN_GESTION: 5}

    conteos = await ContarIncidencias(lector, PLAZOS, tope=10).execute(ADMIN, FiltrosConsulta())

    clasificado = conteos.por_estado[EstadoApi.CLASIFICADO]
    assert (conteos.todos.cantidad, conteos.todos.con_mas) == (10, True)
    assert (clasificado.cantidad, clasificado.con_mas) == (10, True)
    assert conteos.por_estado[EstadoApi.EN_GESTION].con_mas is False
    assert lector.llamadas[0][1][2] == 10
