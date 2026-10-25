import pytest

from app.enums.error_category import ErrorCategory
from app.enums.error_code import ErrorCode
from app.nota.domain.constantes import CONTENIDO_MAX_LENGTH, TITULO_MAX_LENGTH
from app.nota.domain.errors.codigo_nota_invalido import CodigoNotaInvalido
from app.nota.domain.errors.contenido_invalido import ContenidoInvalido
from app.nota.domain.errors.fecha_sin_zona_horaria import FechaSinZonaHoraria
from app.nota.domain.errors.nota_no_encontrada import NotaNoEncontrada
from app.nota.domain.errors.titulo_invalido import TituloInvalido


def test_la_nota_no_encontrada_guarda_el_codigo_como_campo() -> None:
    error = NotaNoEncontrada("NOTA-000009")

    assert error.codigo == "NOTA-000009"
    assert error.details == {"codigo": "NOTA-000009"}
    assert (error.category, error.error_code) == (ErrorCategory.NOT_FOUND, ErrorCode.NOTA_NOT_FOUND)


def test_el_codigo_invalido_guarda_el_valor_como_campo() -> None:
    error = CodigoNotaInvalido("otro")

    assert error.valor == "otro"
    assert error.details == {"valor": "otro"}
    assert (error.category, error.error_code) == (ErrorCategory.VALIDATION, ErrorCode.NOTA_CODIGO_INVALID)


@pytest.mark.parametrize(
    ("error", "maximo", "codigo"),
    [
        (TituloInvalido(), TITULO_MAX_LENGTH, ErrorCode.NOTA_TITULO_INVALID),
        (ContenidoInvalido(), CONTENIDO_MAX_LENGTH, ErrorCode.NOTA_CONTENIDO_INVALID),
    ],
    ids=["titulo", "contenido"],
)
def test_los_errores_de_largo_guardan_el_maximo_como_campo(
    error: TituloInvalido | ContenidoInvalido, maximo: int, codigo: ErrorCode
) -> None:
    assert error.max_length == maximo
    assert error.details == {"max": maximo}
    assert (error.category, error.error_code) == (ErrorCategory.BUSINESS_RULE, codigo)


def test_la_fecha_sin_zona_horaria_es_un_error_interno() -> None:
    error = FechaSinZonaHoraria()

    assert (error.category, error.error_code) == (ErrorCategory.INTERNAL, ErrorCode.INTERNAL_ERROR)
    assert error.details is None
