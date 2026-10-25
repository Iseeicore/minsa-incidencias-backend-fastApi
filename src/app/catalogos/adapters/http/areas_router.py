from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import StringConstraints

from app.catalogos.adapters.http.areas_schemas import PaginaDeAreasResponse
from app.catalogos.domain.area_listada import ConsultaAreas
from app.constants.areas import AREAS_CURSOR_LONGITUD_MAXIMA, AREAS_LIMITE_MAXIMO, AREAS_LIMITE_POR_DEFECTO
from app.constants.incidencias import TEXTO_BUSQUEDA_MAXIMO
from app.constants.textos.errores import MENSAJE_CURSOR_INVALIDO
from app.enums.tipo_area import TipoArea
from app.errors.datos_invalidos import DatosInvalidos
from app.shared.auth_deps import require_session
from app.shared.cursor import decode_int_cursor
from app.shared.http_errors import (
    INTERNAL_RESPONSE,
    RATE_LIMITED_RESPONSE,
    SIN_SESION_RESPONSE,
    VALIDATION_RESPONSE,
    json_example,
)
from app.shared.sesion import SesionActual

if TYPE_CHECKING:
    from app.catalogos.application.listar_areas import ListarAreas

AREAS_EJEMPLO = {
    "items": [
        {
            "id": 1,
            "codigo": "HOSP-01",
            "nombre": "Hospital Uno",
            "tipoArea": "ESTABLECIMIENTO",
            "establecimiento": {"codigoRenipress": "00001234", "nivelAtencion": "II-1", "categoria": "II-1"},
        }
    ],
    "siguiente": None,
    "hayMas": False,
}
AREAS_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {"description": "Página de áreas.", "content": json_example(AREAS_EJEMPLO)}
}
TextoDeBusqueda = Annotated[str, StringConstraints(strip_whitespace=True, max_length=TEXTO_BUSQUEDA_MAXIMO)]


def build_areas_router(listar_areas: ListarAreas) -> APIRouter:
    router = APIRouter(prefix="/areas", tags=["Áreas"])

    @router.get(
        "",
        operation_id="listarAreas",
        response_model=PaginaDeAreasResponse,
        summary="Listar las áreas que la sesión puede ver.",
        description="Página de áreas por cursor; quien no ve todas las áreas solo recibe la suya.",
        responses={
            **AREAS_RESPONSE,
            **VALIDATION_RESPONSE,
            **SIN_SESION_RESPONSE,
            **RATE_LIMITED_RESPONSE,
            **INTERNAL_RESPONSE,
        },
    )
    async def listar(
        sesion: Annotated[SesionActual, Depends(require_session)],
        tipo: Annotated[TipoArea | None, Query()] = None,
        q: Annotated[TextoDeBusqueda | None, Query()] = None,
        limite: Annotated[int, Query(ge=1, le=AREAS_LIMITE_MAXIMO)] = AREAS_LIMITE_POR_DEFECTO,
        cursor: Annotated[str | None, Query(max_length=AREAS_CURSOR_LONGITUD_MAXIMA)] = None,
    ) -> PaginaDeAreasResponse:
        posicion = None
        if cursor:
            posicion = decode_int_cursor(cursor)
            if posicion is None:
                raise DatosInvalidos(details=[{"path": "cursor", "message": MENSAJE_CURSOR_INVALIDO}])
        consulta = ConsultaAreas(limite=limite, despues_de=posicion, tipo=tipo, texto=q or None)
        return PaginaDeAreasResponse.desde_dominio(await listar_areas.execute(sesion, consulta))

    return router
