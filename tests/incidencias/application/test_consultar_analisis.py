import pytest

from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.consultar_analisis import ConsultarAnalisis
from app.incidencias.application.visibilidad import visibilidad_de
from tests.helpers.analisis_en_memoria import AnalisisEnMemoria, una_fila_de_analisis
from tests.helpers.builders import un_caso_consultado, una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

CODIGO = "MINSA-2026-000001"
ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTRANS = una_sesion(roles=("OTRANS",))


async def test_devuelve_el_analisis_guardado_del_caso_con_la_visibilidad_de_la_sesion() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()])
    analisis = AnalisisEnMemoria({ID: una_fila_de_analisis()})

    resultado = await ConsultarAnalisis(casos, analisis).execute(OTRANS, CODIGO)

    assert resultado.codigo == CODIGO
    assert resultado.version_reglas == "reglas-corrupcion-v1.3"
    assert analisis.consultas == [ID]
    assert casos.llamadas == [("buscar_por_codigo", (CODIGO, visibilidad_de(OTRANS)))]


async def test_un_caso_que_no_se_ve_responde_404_con_el_mensaje_del_caso_sin_leer_el_analisis() -> None:
    analisis = AnalisisEnMemoria()

    with pytest.raises(NoEncontrado, match=r"El caso solicitado no existe\."):
        await ConsultarAnalisis(IncidenciasEnMemoria(), analisis).execute(OTRANS, CODIGO)

    assert analisis.consultas == []


async def test_un_caso_sin_analisis_responde_404_con_su_propio_mensaje() -> None:
    casos = IncidenciasEnMemoria([un_caso_consultado()])

    with pytest.raises(NoEncontrado, match="todavía no tiene análisis de clasificación"):
        await ConsultarAnalisis(casos, AnalisisEnMemoria()).execute(OTRANS, CODIGO)
