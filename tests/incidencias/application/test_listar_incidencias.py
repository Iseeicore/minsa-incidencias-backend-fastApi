from datetime import UTC, datetime

from app.incidencias.application.listar_incidencias import ListarIncidencias
from app.incidencias.domain.caso_consultado import CasoConsultado
from app.incidencias.domain.consultas import ConsultaListado, FiltrosConsulta
from app.incidencias.domain.cursores import (
    PosicionDeListado,
    PosicionPorVencer,
    decodificar_cursor,
    decodificar_cursor_por_vencer,
)
from app.incidencias.domain.plazo import PlazosConfigurados
from tests.helpers.builders import un_caso_consultado, una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
ADMIN = una_sesion(roles=("ADMINISTRADOR",))
MARCA = datetime(2026, 10, 24, 7, 0, 0, 123_456, tzinfo=UTC)


def _id(indice: int) -> str:
    return f"aaaaaaaa-aaaa-4aaa-8aaa-{indice:012d}"


def _casos(cantidad: int) -> list[CasoConsultado]:
    return [
        un_caso_consultado(id=_id(indice), codigo=f"MINSA-2026-{indice:06d}", fecha_creacion=MARCA)
        for indice in range(1, cantidad + 1)
    ]


async def test_pide_una_fila_de_mas_y_arma_el_cursor_del_ultimo_cuando_hay_mas() -> None:
    lector = IncidenciasEnMemoria(_casos(3))

    pagina = await ListarIncidencias(lector, PLAZOS).execute(ADMIN, ConsultaListado(limite=2))

    assert [caso.codigo for caso in pagina.items] == ["MINSA-2026-000001", "MINSA-2026-000002"]
    assert pagina.hay_mas is True
    assert decodificar_cursor(pagina.siguiente or "") == PosicionDeListado(MARCA.replace(microsecond=123_000), _id(2))
    nombre, argumentos = lector.llamadas[0]
    assert (nombre, argumentos[2]) == ("listar", 3)


async def test_sin_mas_filas_no_hay_cursor() -> None:
    pagina = await ListarIncidencias(IncidenciasEnMemoria(_casos(2)), PLAZOS).execute(ADMIN, ConsultaListado(limite=2))

    assert (pagina.siguiente, pagina.hay_mas, len(pagina.items)) == (None, False, 2)


async def test_los_resumenes_traen_las_acciones_de_la_sesion() -> None:
    pagina = await ListarIncidencias(IncidenciasEnMemoria(_casos(1)), PLAZOS).execute(ADMIN, ConsultaListado(limite=5))

    assert [accion.value for accion in pagina.items[0].acciones] == ["confirmar", "corregir", "archivar"]


async def test_con_el_filtro_de_plazo_usa_la_consulta_de_proximos_a_vencer_y_su_cursor() -> None:
    lector = IncidenciasEnMemoria(_casos(3))
    posicion = PosicionPorVencer(MARCA, _id(9))
    consulta = ConsultaListado(limite=2, filtros=FiltrosConsulta(por_vencer=True), despues_de_por_vencer=posicion)

    pagina = await ListarIncidencias(lector, PLAZOS).execute(ADMIN, consulta)

    nombre, argumentos = lector.llamadas[0]
    assert nombre == "listar_proximos_a_vencer"
    assert (argumentos[1].aviso_horas, argumentos[2], argumentos[3]) == (48, 3, posicion)
    cursor = decodificar_cursor_por_vencer(pagina.siguiente or "")
    assert cursor is not None
    assert cursor.id == _id(2)
    assert cursor.vence_en == datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


async def test_el_cursor_por_vencer_usa_la_fecha_de_llegada_si_el_caso_no_tiene_vencimiento() -> None:
    casos = [un_caso_consultado(id=_id(i), vence_atencion_en=None, fecha_creacion=MARCA) for i in (1, 2)]
    consulta = ConsultaListado(limite=1, filtros=FiltrosConsulta(por_vencer=True))

    pagina = await ListarIncidencias(IncidenciasEnMemoria(casos), PLAZOS).execute(ADMIN, consulta)

    cursor = decodificar_cursor_por_vencer(pagina.siguiente or "")
    assert cursor is not None
    assert cursor.vence_en == MARCA.replace(microsecond=123_000)
