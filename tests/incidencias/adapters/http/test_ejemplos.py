from app.incidencias.adapters.http.ejemplos import (
    ANALISIS_EJEMPLO,
    CASO_EJEMPLO,
    DERIVACION_EJEMPLO,
    DETALLE_EJEMPLO,
    INDICADORES_EJEMPLO,
    IPRESS_EJEMPLO,
    RESUMEN_DE_IPRESS_EJEMPLO,
)
from app.incidencias.adapters.http.schemas import CasoDetalleResponse, CasoResumenResponse
from app.incidencias.adapters.http.schemas_de_analisis import AnalisisIaResponse
from app.incidencias.adapters.http.schemas_de_derivacion import DerivacionResumenResponse
from app.incidencias.adapters.http.schemas_de_indicadores import IndicadoresResponse, ResumenDeIpressResponse
from app.incidencias.adapters.http.schemas_de_ipress import IpressListadaResponse


def test_el_ejemplo_de_resumen_cumple_el_esquema_de_respuesta() -> None:
    assert CasoResumenResponse.model_validate(CASO_EJEMPLO).codigo == "MINSA-2026-000001"


def test_el_ejemplo_de_detalle_cumple_el_esquema_de_respuesta() -> None:
    detalle = CasoDetalleResponse.model_validate(DETALLE_EJEMPLO)

    assert detalle.codigo == CASO_EJEMPLO["codigo"]
    assert len(detalle.historial) == 1


def test_el_ejemplo_de_derivacion_cumple_el_esquema_de_respuesta() -> None:
    assert DerivacionResumenResponse.model_validate(DERIVACION_EJEMPLO).destino.codigo_renipress == "1"


def test_el_ejemplo_de_indicadores_cumple_el_esquema_de_respuesta() -> None:
    assert IndicadoresResponse.model_validate(INDICADORES_EJEMPLO).tiempo_promedio_horas == 18.5


def test_los_ejemplos_de_ipress_cumplen_el_esquema_de_respuesta() -> None:
    assert ResumenDeIpressResponse.model_validate(RESUMEN_DE_IPRESS_EJEMPLO).total == 5
    assert IpressListadaResponse.model_validate(IPRESS_EJEMPLO).establecimiento.codigo_renipress == "1"


def test_el_ejemplo_de_analisis_cumple_el_esquema_de_respuesta() -> None:
    analisis = AnalisisIaResponse.model_validate(ANALISIS_EJEMPLO)

    assert analisis.ficha_derivacion is not None
    assert analisis.ficha_derivacion.codigo_entidad == "sis"
