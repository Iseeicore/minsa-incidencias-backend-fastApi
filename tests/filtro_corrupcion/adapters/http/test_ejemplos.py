from app.filtro_corrupcion.adapters.http.ejemplos import EVALUACION_DE_CORRUPCION_EJEMPLO
from app.filtro_corrupcion.adapters.http.schemas import EvaluacionCorrupcionResponse


def test_el_ejemplo_de_evaluacion_cumple_el_esquema_de_respuesta() -> None:
    evaluacion = EvaluacionCorrupcionResponse.model_validate(EVALUACION_DE_CORRUPCION_EJEMPLO)

    assert evaluacion.propuesta_corrupcion is True
    assert evaluacion.combinacion is not None
    assert evaluacion.combinacion.confianza == 84.5
