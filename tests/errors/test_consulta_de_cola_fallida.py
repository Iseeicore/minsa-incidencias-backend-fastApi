from app.errors.consulta_de_cola_fallida import ConsultaDeColaFallida


def test_el_error_de_la_cola_explica_que_no_se_pudo_consultar() -> None:
    assert str(ConsultaDeColaFallida()) == "No se pudo consultar la cola de incidencias por clasificar."
    assert isinstance(ConsultaDeColaFallida(), RuntimeError)
