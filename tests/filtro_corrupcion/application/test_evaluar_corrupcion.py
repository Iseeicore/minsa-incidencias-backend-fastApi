from app.filtro_corrupcion.application.evaluar_corrupcion import EvaluarCorrupcion, SolicitudDeEvaluacion
from app.filtro_corrupcion.domain.tipos import ContextoEvaluacion

TEXTO = "La jefa del SIS me pidio plata para atenderme"


def test_evalua_el_texto_con_las_reglas_y_no_combina_si_no_se_pide() -> None:
    evaluacion = EvaluarCorrupcion().execute(SolicitudDeEvaluacion(TEXTO, ContextoEvaluacion()))

    assert evaluacion.resultado.propuesta_corrupcion is True
    assert evaluacion.combinacion is None


def test_si_se_pide_combina_con_el_peso_de_la_ia_ya_normalizado() -> None:
    solicitud = SolicitudDeEvaluacion(TEXTO, ContextoEvaluacion(), combinar_con_ia=True, peso_ia=6.4)

    combinacion = EvaluarCorrupcion().execute(solicitud).combinacion

    assert combinacion is not None
    assert (combinacion.peso_ia, combinacion.puntaje_total) == (6, 11)


def test_pedir_la_combinacion_sin_peso_equivale_a_no_haber_tenido_modelo() -> None:
    solicitud = SolicitudDeEvaluacion(TEXTO, ContextoEvaluacion(), combinar_con_ia=True, peso_ia=None)

    combinacion = EvaluarCorrupcion().execute(solicitud).combinacion

    assert combinacion is not None
    assert combinacion.peso_ia is None
    assert combinacion.acuerdo.value == "SIN_MODELO"


def test_el_contexto_llega_al_motor() -> None:
    sin_entidades = SolicitudDeEvaluacion(TEXTO, ContextoEvaluacion(entidades=()))

    assert EvaluarCorrupcion().execute(sin_entidades).resultado.entidad is None
