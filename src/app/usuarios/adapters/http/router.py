from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

from app.enums.error_code import ErrorCode
from app.enums.vista_codigo import VistaCodigo
from app.shared.auth_deps import require_vista
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
from app.usuarios.adapters.http.consulta import consulta_de_usuarios, identificador_de_usuario
from app.usuarios.adapters.http.schemas import (
    CambiosDeUsuarioRequest,
    CreacionDeUsuarioRequest,
    PaginaDeUsuariosResponse,
    UsuarioActualizadoResponse,
    UsuarioConClaveResponse,
    UsuarioResponse,
)
from app.usuarios.domain.pedidos import ConsultaUsuarios

if TYPE_CHECKING:
    from app.usuarios.application.actualizar_usuario import ActualizarUsuario
    from app.usuarios.application.crear_usuario import CrearUsuario
    from app.usuarios.application.listar_usuarios import ListarUsuarios
    from app.usuarios.application.restablecer_clave import RestablecerClave

USUARIO_EJEMPLO = {
    "id": "11111111-1111-4111-8111-111111111111",
    "nombreCompleto": "Ana Torres",
    "correo": "ana.torres@minsa.gob.pe",
    "rol": "GESTOR",
    "activo": True,
    "area": {"codigo": "HOSP-01", "nombre": "Hospital Uno"},
}
USUARIOS_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {
        "description": "Página de usuarios.",
        "content": json_example({"items": [USUARIO_EJEMPLO], "siguiente": None, "hayMas": False}),
    }
}
USUARIO_CREADO_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.CREATED: {
        "description": "Usuario creado.",
        "content": json_example({"usuario": USUARIO_EJEMPLO, "claveInicial": "Zq7mK2xWb9PdE4tNvR5h"}),
    }
}
USUARIO_ACTUALIZADO_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {"description": "Usuario actualizado.", "content": json_example({"usuario": USUARIO_EJEMPLO})}
}
CLAVE_RESTABLECIDA_RESPONSE: dict[int | str, dict[str, object]] = {
    HTTPStatus.OK: {
        "description": "Clave restablecida.",
        "content": json_example({"usuario": USUARIO_EJEMPLO, "claveInicial": "Zq7mK2xWb9PdE4tNvR5h"}),
    }
}
FORBIDDEN_RESPONSE = error_response(HTTPStatus.FORBIDDEN, ErrorCode.FORBIDDEN)
CONFLICT_RESPONSE = error_response(HTTPStatus.CONFLICT, ErrorCode.CONFLICT)
UNPROCESSABLE_RESPONSE = error_response(HTTPStatus.UNPROCESSABLE_ENTITY, ErrorCode.UNPROCESSABLE)
NOT_FOUND_RESPONSE = error_response(HTTPStatus.NOT_FOUND, ErrorCode.NOT_FOUND)

GestionDeUsuariosDep = Annotated[SesionActual, Depends(require_vista(VistaCodigo.USUARIOS))]
UsuarioIdDep = Annotated[str, Depends(identificador_de_usuario)]
ConsultaDep = Annotated[ConsultaUsuarios, Depends(consulta_de_usuarios)]


def build_usuarios_router(
    listar: ListarUsuarios,
    crear: CrearUsuario,
    actualizar: ActualizarUsuario,
    restablecer: RestablecerClave,
) -> APIRouter:
    router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
    comunes = {**SIN_SESION_RESPONSE, **FORBIDDEN_RESPONSE, **RATE_LIMITED_RESPONSE, **INTERNAL_RESPONSE}

    @router.get(
        "",
        operation_id="listarUsuarios",
        response_model=PaginaDeUsuariosResponse,
        summary="Listar los usuarios que la sesión puede gestionar.",
        description="Página de usuarios por cursor, con búsqueda por nombre o correo y filtro por área.",
        responses={**USUARIOS_RESPONSE, **VALIDATION_RESPONSE, **comunes},
    )
    async def listar_usuarios(sesion: GestionDeUsuariosDep, consulta: ConsultaDep) -> PaginaDeUsuariosResponse:
        return PaginaDeUsuariosResponse.desde_dominio(await listar.execute(sesion, consulta))

    @router.post(
        "",
        operation_id="crearUsuario",
        status_code=HTTPStatus.CREATED,
        response_model=UsuarioConClaveResponse,
        summary="Crear un usuario con una clave inicial.",
        description="Crea el usuario con un rol y devuelve la clave inicial una sola vez.",
        responses={
            **USUARIO_CREADO_RESPONSE,
            **VALIDATION_RESPONSE,
            **PAYLOAD_TOO_LARGE_RESPONSE,
            **CONFLICT_RESPONSE,
            **UNPROCESSABLE_RESPONSE,
            **comunes,
        },
    )
    async def crear_usuario(sesion: GestionDeUsuariosDep, cuerpo: CreacionDeUsuarioRequest) -> UsuarioConClaveResponse:
        return UsuarioConClaveResponse.desde_dominio(await crear.execute(sesion, cuerpo.a_dominio()))

    @router.patch(
        "/{id}",
        operation_id="actualizarUsuario",
        response_model=UsuarioActualizadoResponse,
        summary="Actualizar los datos, el rol, el área o la vigencia de un usuario.",
        description="Aplica los cambios indicados; cambiar el rol o desactivar cierra sus sesiones.",
        responses={
            **USUARIO_ACTUALIZADO_RESPONSE,
            **VALIDATION_RESPONSE,
            **PAYLOAD_TOO_LARGE_RESPONSE,
            **NOT_FOUND_RESPONSE,
            **CONFLICT_RESPONSE,
            **UNPROCESSABLE_RESPONSE,
            **comunes,
        },
    )
    async def actualizar_usuario(
        sesion: GestionDeUsuariosDep,
        id: UsuarioIdDep,  # noqa: A002
        cuerpo: CambiosDeUsuarioRequest,
    ) -> UsuarioActualizadoResponse:
        usuario = await actualizar.execute(sesion, id, cuerpo.a_dominio())
        return UsuarioActualizadoResponse(usuario=UsuarioResponse.desde_dominio(usuario))

    @router.post(
        "/{id}/restablecer-clave",
        operation_id="restablecerClaveDeUsuario",
        response_model=UsuarioConClaveResponse,
        summary="Restablecer la clave de un usuario.",
        description="Genera una clave nueva, la devuelve una sola vez y cierra las sesiones del usuario.",
        responses={**CLAVE_RESTABLECIDA_RESPONSE, **NOT_FOUND_RESPONSE, **comunes},
    )
    async def restablecer_clave(sesion: GestionDeUsuariosDep, id: UsuarioIdDep) -> UsuarioConClaveResponse:  # noqa: A002
        return UsuarioConClaveResponse.desde_dominio(await restablecer.execute(sesion, id))

    return router
