from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Body, Depends

from app.constants.filtro_corrupcion import (
    ENTIDADES_EVALUACION_MAXIMO,
    LONGITUD_MINIMA_TEXTO_CORRUPCION,
    PESO_MAXIMO_IA,
    TEXTO_EVALUACION_MAXIMO,
    VERSION_REGLAS_CORRUPCION,
)
from app.enums.error_code import ErrorCode
from app.enums.rol_codigo import RolCodigo
from app.errors.datos_invalidos import DatosInvalidos
from app.filtro_corrupcion.adapters.http.ejemplos import EVALUACION_DE_CORRUPCION_EJEMPLO
from app.filtro_corrupcion.adapters.http.schemas import EvaluacionCorrupcionResponse, EvaluacionRequest
from app.shared.auth_deps import require_rol
from app.shared.http_errors import (
    INTERNAL_RESPONSE,
    PAYLOAD_TOO_LARGE_RESPONSE,
    RATE_LIMITED_RESPONSE,
    SIN_SESION_RESPONSE,
    VALIDATION_RESPONSE,
    error_response,
    json_example,
)
from app.shared.sesion import SesionActual

if TYPE_CHECKING:
    from app.filtro_corrupcion.application.evaluar_corrupcion import EvaluarCorrupcion

ROLES = f"{RolCodigo.ADMINISTRADOR}, {RolCodigo.GESTOR}, {RolCodigo.OTRANS}"
FORBIDDEN_RESPONSE = error_response(HTTPStatus.FORBIDDEN, ErrorCode.FORBIDDEN)
EVALUACION_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {
        "description": "Resultado de las reglas, con la combinación si se envió pesoIa.",
        "content": json_example(EVALUACION_DE_CORRUPCION_EJEMPLO),
    }
}
PuedeProbarDep = Annotated[
    SesionActual, Depends(require_rol(RolCodigo.ADMINISTRADOR, RolCodigo.GESTOR, RolCodigo.OTRANS))
]
CuerpoDep = Annotated[EvaluacionRequest | None, Body()]


def build_filtro_corrupcion_router(evaluar: EvaluarCorrupcion) -> APIRouter:
    router = APIRouter(prefix="/filtro-corrupcion", tags=["Filtro de corrupción"])

    @router.post(
        "/evaluar",
        operation_id="evaluarTextoCorrupcion",
        response_model=EvaluacionCorrupcionResponse,
        response_model_exclude_unset=True,
        summary="Probar el filtro de corrupción por reglas sobre un texto.",
        description=(
            f"Exige uno de los roles {ROLES}. Evalúa el texto (hasta {TEXTO_EVALUACION_MAXIMO} caracteres) con las "
            f"reglas {VERSION_REGLAS_CORRUPCION}, sin IA, sin base de datos y sin guardar ni registrar el texto. "
            f"Solo propone: nunca asigna destino. Con menos de {LONGITUD_MINIMA_TEXTO_CORRUPCION} caracteres tras "
            "recortar responde aplica: false y el faltante DATOS_INSUFICIENTES. Sin entidades usa el catálogo "
            f"oficial y entidades: [] desactiva la detección de entidad (máximo {ENTIDADES_EVALUACION_MAXIMO}). Si el "
            f"cuerpo trae pesoIa, un número que se redondea y acota de 0 a {PESO_MAXIMO_IA} o null si el modelo no "
            "estuvo disponible, la respuesta agrega combinacion con la suma de reglas e IA."
        ),
        responses={
            **EVALUACION_RESPONSE,
            **VALIDATION_RESPONSE,
            **SIN_SESION_RESPONSE,
            **FORBIDDEN_RESPONSE,
            **PAYLOAD_TOO_LARGE_RESPONSE,
            **RATE_LIMITED_RESPONSE,
            **INTERNAL_RESPONSE,
        },
    )
    def evaluar_texto(sesion: PuedeProbarDep, cuerpo: CuerpoDep = None) -> EvaluacionCorrupcionResponse:
        del sesion
        if cuerpo is None:
            raise DatosInvalidos(details=[{"path": "texto", "message": "Field required"}])
        return EvaluacionCorrupcionResponse.desde_dominio(evaluar.execute(cuerpo.a_solicitud()))

    return router
