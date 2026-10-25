from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from app.constants.textos.reglas_de_la_base import (
    CHECK_VIOLATION_SQLSTATE,
    MENSAJE_REGLA_DESCONOCIDA,
    REGLAS_DE_LA_BASE,
)
from app.enums.error_code import ErrorCode
from app.errors.conflicto import Conflicto
from app.errors.no_procesable import NoProcesable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from app.errors.domain_error import DomainError


def sqlstate_of(error: IntegrityError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


def constraint_of(error: IntegrityError) -> str | None:
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None)


def rule_error(error: IntegrityError) -> DomainError | None:
    if sqlstate_of(error) != CHECK_VIOLATION_SQLSTATE:
        return None
    message = str(error.orig)
    rule = next((candidate for candidate in REGLAS_DE_LA_BASE if candidate.fragmento in message), None)
    if rule is not None and rule.corregible:
        return NoProcesable(rule.mensaje)
    if rule is None:
        return Conflicto(MENSAJE_REGLA_DESCONOCIDA)
    return Conflicto(rule.mensaje, rule.codigo or ErrorCode.CONFLICT)


@contextmanager
def translate_database_rules() -> Iterator[None]:
    try:
        yield
    except IntegrityError as error:
        translated = rule_error(error)
        if translated is None:
            raise
        raise translated from error
