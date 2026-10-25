from app.incidencias.application.incidencias_por_vencer import IncidenciasPorVencer
from app.incidencias.domain.caso_consultado import ConteoPorVencer
from app.incidencias.domain.plazo import PlazosConfigurados
from app.shared.permisos import PERMISOS_POR_ROL
from tests.helpers.builders import un_caso_consultado, una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)


async def test_el_resumen_separa_por_vencer_de_vencidos_y_lista_los_casos() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()])
    lector.conteo_por_vencer = ConteoPorVencer(total=5, vencidos=2)

    resumen = await IncidenciasPorVencer(lector, PLAZOS).execute(una_sesion(roles=("ADMINISTRADOR",)))

    assert (resumen.total, resumen.por_vencer, resumen.vencidos) == (5, 3, 2)
    assert [caso.codigo for caso in resumen.casos] == ["MINSA-2026-000001"]


async def test_el_administrador_avisa_de_todo_lo_abierto_y_los_demas_solo_de_lo_que_les_toca() -> None:
    lector = IncidenciasEnMemoria()

    await IncidenciasPorVencer(lector, PLAZOS).execute(una_sesion(roles=("ADMINISTRADOR",)))
    await IncidenciasPorVencer(lector, PLAZOS).execute(una_sesion(roles=("GESTOR",)))

    pendientes = [argumentos[2] for nombre, argumentos in lector.llamadas if nombre == "contar_por_vencer"]
    assert pendientes == [None, PERMISOS_POR_ROL["GESTOR"].acciones]


async def test_la_lista_se_limita_a_diez_casos_con_el_aviso_configurado() -> None:
    lector = IncidenciasEnMemoria()

    await IncidenciasPorVencer(lector, PLAZOS).execute(una_sesion(roles=("GESTOR",)))

    argumentos = next(argumentos for nombre, argumentos in lector.llamadas if nombre == "listar_por_vencer")
    assert (argumentos[1], argumentos[2]) == (48, 10)
