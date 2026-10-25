from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.errors.alcance_de_incidencia_invalido import AlcanceDeIncidenciaInvalido
from app.errors.conexion_perdida import ConexionPerdida
from app.errors.demasiadas_conexiones import DemasiadasConexiones


def test_demasiadas_conexiones_es_un_error_de_limite_con_su_propio_codigo() -> None:
    error = DemasiadasConexiones()

    assert (error.category, error.error_code) == (ErrorCategory.RATE_LIMITED, ErrorCode.DEMASIADAS_CONEXIONES)
    assert error.headers is None


def test_los_errores_de_la_escucha_explican_que_paso() -> None:
    assert "alcance" in str(AlcanceDeIncidenciaInvalido())
    assert isinstance(AlcanceDeIncidenciaInvalido(), ValueError)
    assert "conexión" in str(ConexionPerdida())
