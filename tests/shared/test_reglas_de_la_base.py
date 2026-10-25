import pytest
from psycopg.errors import CheckViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError

from app.constants.textos.reglas_de_la_base import REGLAS_DE_LA_BASE
from app.enums.error_code import ErrorCode
from app.errors.conflicto import Conflicto
from app.errors.no_procesable import NoProcesable
from app.shared.reglas_de_la_base import constraint_of, rule_error, sqlstate_of, translate_database_rules


def _check(mensaje: str) -> IntegrityError:
    return IntegrityError("SQL", {}, CheckViolation(mensaje))


def test_una_regla_corregible_es_no_procesable_con_su_mensaje() -> None:
    error = rule_error(_check("tabla: exigen un area de destino para continuar"))

    assert isinstance(error, NoProcesable)
    assert error.message == "El caso necesita un área de destino para derivarlo o tomarlo."


def test_una_regla_no_corregible_es_conflicto() -> None:
    error = rule_error(_check("la categoria ya se corrigio una vez"))

    assert isinstance(error, Conflicto)
    assert (error.error_code, error.message) == (ErrorCode.CONFLICT, "La categoría ya se corrigió una vez.")


def test_el_tope_de_usuarios_del_establecimiento_conserva_su_codigo() -> None:
    error = rule_error(_check("el establecimiento ya tiene 3 usuarios activos"))

    assert isinstance(error, Conflicto)
    assert error.error_code is ErrorCode.LIMITE_USUARIOS_ESTABLECIMIENTO
    assert error.message.startswith("Este establecimiento ya tiene 3 usuarios activos")


def test_una_regla_desconocida_es_un_conflicto_generico() -> None:
    error = rule_error(_check("algo que nadie conoce"))

    assert isinstance(error, Conflicto)
    assert error.message == "El cambio no cumple una regla del caso."


@pytest.mark.parametrize("regla", REGLAS_DE_LA_BASE, ids=lambda regla: regla.fragmento[:40])
def test_cada_regla_conocida_se_reconoce_por_su_fragmento(regla: object) -> None:
    error = rule_error(_check(f"prefijo {regla.fragmento} sufijo"))  # type: ignore[attr-defined]

    assert error is not None
    assert error.message == regla.mensaje  # type: ignore[attr-defined]


def test_un_error_que_no_es_de_regla_no_se_traduce() -> None:
    unico = IntegrityError("SQL", {}, UniqueViolation("duplicado"))

    assert rule_error(unico) is None


def _lanzar(error: Exception) -> None:
    with translate_database_rules():
        raise error


def test_el_gestor_de_contexto_traduce_las_reglas() -> None:
    with pytest.raises(Conflicto):
        _lanzar(_check("la confirmacion se registra una sola vez"))


def test_el_gestor_de_contexto_deja_pasar_lo_que_no_es_una_regla() -> None:
    with pytest.raises(IntegrityError):
        _lanzar(IntegrityError("SQL", {}, UniqueViolation("duplicado")))
    with pytest.raises(ValueError, match="otro"):
        _lanzar(ValueError("otro"))


def test_se_lee_el_sqlstate_y_la_restriccion_del_error() -> None:
    error = IntegrityError("SQL", {}, UniqueViolation("duplicado"))

    assert sqlstate_of(error) == "23505"
    assert constraint_of(error) is None
