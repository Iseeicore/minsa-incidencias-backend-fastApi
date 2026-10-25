from app.incidencias.adapters.http.ejemplos import CASO_EJEMPLO, DETALLE_EJEMPLO
from app.incidencias.adapters.http.schemas import CasoDetalleResponse, CasoResumenResponse


def test_el_ejemplo_de_resumen_cumple_el_esquema_de_respuesta() -> None:
    assert CasoResumenResponse.model_validate(CASO_EJEMPLO).codigo == "MINSA-2026-000001"


def test_el_ejemplo_de_detalle_cumple_el_esquema_de_respuesta() -> None:
    detalle = CasoDetalleResponse.model_validate(DETALLE_EJEMPLO)

    assert detalle.codigo == CASO_EJEMPLO["codigo"]
    assert len(detalle.historial) == 1
