import pytest

from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.consultar_incidencia import ConsultarIncidencia
from app.incidencias.domain.plazo import PlazosConfigurados
from tests.helpers.builders import un_caso_consultado, una_evidencia, una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
ADMIN = una_sesion(roles=("ADMINISTRADOR",))


async def test_devuelve_el_detalle_con_las_evidencias_del_caso() -> None:
    evidencia = una_evidencia()
    lector = IncidenciasEnMemoria([un_caso_consultado()], evidencias=[evidencia])

    detalle = await ConsultarIncidencia(lector, PLAZOS).execute(ADMIN, "MINSA-2026-000001")

    assert detalle.resumen.codigo == "MINSA-2026-000001"
    assert [e.id for e in detalle.evidencias] == ["0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"]
    assert {nombre for nombre, _ in lector.llamadas} == {"buscar_por_codigo", "evidencias", "historial"}


async def test_un_caso_que_no_existe_o_no_es_visible_responde_404_con_el_mensaje_del_caso() -> None:
    with pytest.raises(NoEncontrado, match=r"El caso solicitado no existe\."):
        await ConsultarIncidencia(IncidenciasEnMemoria(), PLAZOS).execute(ADMIN, "MINSA-2026-000099")
