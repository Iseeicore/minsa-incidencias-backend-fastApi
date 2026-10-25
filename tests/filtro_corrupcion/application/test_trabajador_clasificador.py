import pytest

from app.constants.textos.procesos import (
    EVENTO_ALARMA_SIN_CLASIFICAR,
    EVENTO_CICLO_DEL_CLASIFICADOR,
    EVENTO_FALLO_EL_CICLO_DEL_CLASIFICADOR,
)
from app.errors.consulta_de_cola_fallida import ConsultaDeColaFallida
from app.filtro_corrupcion.application.clasificar_incidencias import ClasificadorIncidencias
from app.filtro_corrupcion.application.trabajador_clasificador import TrabajadorClasificador
from app.filtro_corrupcion.domain.cola_de_clasificacion import CasoPendiente, FilaAlarma
from tests.helpers.clasificador_en_memoria import AlmacenDelClasificador
from tests.helpers.registro_en_memoria import RegistroEnMemoria

QUEJA = "El personal fue grosero y prepotente conmigo en la ventanilla del hospital"


def _trabajador(almacen: AlmacenDelClasificador, registro: RegistroEnMemoria) -> TrabajadorClasificador:
    return TrabajadorClasificador(ClasificadorIncidencias(almacen), almacen, registro)


async def test_un_ciclo_sin_trabajo_ni_atrasos_no_deja_registro() -> None:
    registro = RegistroEnMemoria()

    await _trabajador(AlmacenDelClasificador(), registro).ejecutar_ciclo()

    assert registro.eventos == []


async def test_un_ciclo_con_casos_informa_el_resumen_de_la_cola() -> None:
    almacen = AlmacenDelClasificador([CasoPendiente("id-1", "MINSA-2026-000001", QUEJA, None)])
    registro = RegistroEnMemoria()

    await _trabajador(almacen, registro).ejecutar_ciclo()

    assert registro.eventos == [
        ("info", EVENTO_CICLO_DEL_CLASIFICADOR, {"clasificadas": 1, "fallos": 0, "abandonadas": 0, "a_otrans": 0})
    ]


async def test_si_hay_casos_atrasados_avisa_con_una_alarma() -> None:
    almacen = AlmacenDelClasificador()
    almacen.fila_de_alarma = FilaAlarma(3, 12.5, ("MINSA-2026-000001",))
    registro = RegistroEnMemoria()

    await _trabajador(almacen, registro).ejecutar_ciclo()

    assert registro.eventos == [
        (
            "warning",
            EVENTO_ALARMA_SIN_CLASIFICAR,
            {"atrasados": 3, "minutos_del_mas_antiguo": 12.5, "codigos": ["MINSA-2026-000001"], "abandonados": 0},
        )
    ]


async def test_si_el_ciclo_falla_lo_registra_sin_propagar_el_error() -> None:
    almacen = AlmacenDelClasificador()
    almacen.falla_al_consultar_la_cola = RuntimeError("sin base")
    registro = RegistroEnMemoria()

    await _trabajador(almacen, registro).ejecutar_ciclo()

    assert registro.eventos == [("error", EVENTO_FALLO_EL_CICLO_DEL_CLASIFICADOR, {"error": "ConsultaDeColaFallida"})]


async def test_ejecutar_deja_pasar_el_error_para_que_el_proceso_externo_se_detenga() -> None:
    almacen = AlmacenDelClasificador()
    almacen.falla_al_consultar_la_cola = RuntimeError("sin base")

    with pytest.raises(ConsultaDeColaFallida):
        await _trabajador(almacen, RegistroEnMemoria()).ejecutar()
