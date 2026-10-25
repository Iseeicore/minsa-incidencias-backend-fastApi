from app.enums.periodo_indicadores import PeriodoIndicadores
from app.incidencias.adapters.http.schemas_de_indicadores import IndicadoresResponse, ResumenDeIpressResponse
from app.incidencias.application.armar_indicadores import resumir_ipress
from app.incidencias.application.obtener_indicadores import ObtenerIndicadores
from app.incidencias.domain.plazo import PlazosConfigurados
from app.shared.sesion import SesionActual
from tests.helpers.builders import un_area_de_sesion, una_sesion
from tests.helpers.indicadores_en_memoria import IndicadoresEnMemoria

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)


async def _cuerpo(sesion: SesionActual) -> dict[str, object]:
    indicadores = await ObtenerIndicadores(IndicadoresEnMemoria(), PLAZOS).execute(
        sesion, PeriodoIndicadores.SIETE_DIAS
    )
    return IndicadoresResponse.desde_dominio(indicadores).model_dump(by_alias=True, mode="json")


async def test_los_indicadores_se_serializan_con_los_nombres_del_contrato() -> None:
    cuerpo = await _cuerpo(una_sesion(roles=("GESTOR",), area=un_area_de_sesion(id=3)))

    assert cuerpo["periodo"] == "7d"
    assert cuerpo["generadoEn"] == "2026-10-24T12:00:00.456Z"
    assert cuerpo["alcance"] == {
        "tipo": "AREA",
        "area": {"codigo": "HOSP-01", "nombre": "Hospital Uno", "tipo": "ESTABLECIMIENTO"},
    }
    assert cuerpo["tarjetas"][0] == {"codigo": "recibidos", "valor": 12, "anterior": 9}  # type: ignore[index]
    assert cuerpo["tarjetas"][1] == {"codigo": "pendientes", "valor": 4, "anterior": None}  # type: ignore[index]
    assert cuerpo["tiempoPromedioHoras"] == 18.5
    assert len(cuerpo["porEstado"]) == 6  # type: ignore[arg-type]


async def test_un_alcance_total_no_lleva_area() -> None:
    cuerpo = await _cuerpo(una_sesion(roles=("ADMINISTRADOR",)))

    assert cuerpo["alcance"] == {"tipo": "TODO", "area": None}


def test_el_resumen_de_una_ipress_se_serializa_en_camel_case() -> None:
    cuerpo = ResumenDeIpressResponse.desde_dominio(resumir_ipress([])).model_dump(by_alias=True, mode="json")

    assert cuerpo["enGestion"] == 0
    assert cuerpo["porCategoria"][-1] == {"categoria": "sin-categoria", "cantidad": 0}
    assert len(cuerpo["porCategoria"]) == 5
