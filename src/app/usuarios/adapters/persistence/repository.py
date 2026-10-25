from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from app.constants.textos.reglas_de_la_base import UNIQUE_VIOLATION_SQLSTATE
from app.constants.usuarios import RESTRICCION_CORREO_UNICO
from app.errors.correo_repetido import CorreoRepetido
from app.shared.database import translate_database_errors
from app.shared.reglas_de_la_base import constraint_of, sqlstate_of
from app.shared.text_search import like_pattern
from app.shared.transaction import transaction
from app.usuarios.adapters.persistence import consultas
from app.usuarios.domain.usuario_gestionado import UsuarioGestionado

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.engine import Row
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

    from app.enums.rol_codigo import RolCodigo
    from app.shared.cursor import PosicionPorNombre
    from app.usuarios.domain.pedidos import FiltrosDeUsuarios, NuevoUsuarioFila, RestriccionDeArea


def _usuario_de(fila: Row[tuple[object, ...]]) -> UsuarioGestionado:
    return UsuarioGestionado(
        id=str(fila.id),
        nombre_completo=fila.nombre_completo,
        correo=fila.correo,
        activo=fila.activo,
        rol=fila.rol,
        area_id=fila.area_id,
        area_codigo=fila.area_codigo,
        area_nombre=fila.area_nombre,
    )


def _restriccion(restriccion: RestriccionDeArea | None) -> dict[str, object]:
    return {
        "filtrar_area": restriccion is not None,
        "solo_area_id": restriccion.area_id if restriccion is not None else None,
    }


class SqlUsuarioReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def listar(
        self, filtros: FiltrosDeUsuarios, limite: int, despues_de: PosicionPorNombre[str] | None
    ) -> list[UsuarioGestionado]:
        parametros = {
            **_restriccion(filtros.restriccion_de_area),
            "area_codigo": filtros.area_codigo,
            "patron": like_pattern(filtros.texto),
            "hay_cursor": despues_de is not None,
            "cursor_nombre": despues_de.nombre if despues_de is not None else None,
            "cursor_id": despues_de.id if despues_de is not None else None,
            "limite": limite,
        }
        with translate_database_errors():
            async with self._engine.connect() as connection:
                filas = (await connection.execute(consultas.LISTAR, parametros)).all()
        return [_usuario_de(fila) for fila in filas]


class SqlUsuarioTransaction:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def buscar_por_id(
        self, usuario_id: str, restriccion: RestriccionDeArea | None, *, bloquear: bool = False
    ) -> UsuarioGestionado | None:
        consulta = consultas.BUSCAR_POR_ID_BLOQUEANDO if bloquear else consultas.BUSCAR_POR_ID
        fila = (
            await self._connection.execute(consulta, {"usuario_id": usuario_id, **_restriccion(restriccion)})
        ).first()
        return None if fila is None else _usuario_de(fila)

    async def area_activa(self, codigo: str) -> int | None:
        return (await self._connection.execute(consultas.AREA_ACTIVA, {"codigo": codigo})).scalar_one_or_none()

    async def rol_activo(self, rol: RolCodigo) -> bool:
        return bool((await self._connection.execute(consultas.ROL_ACTIVO, {"rol": rol.value})).scalar_one())

    async def correo_existe(self, correo: str) -> bool:
        return bool((await self._connection.execute(consultas.CORREO_EXISTE, {"correo": correo})).scalar_one())

    async def crear(self, datos: NuevoUsuarioFila) -> str:
        parametros = {
            "nombre_completo": datos.nombre_completo,
            "correo": datos.correo,
            "huella": datos.huella,
            "area_id": datos.area_id,
        }
        try:
            resultado = await self._connection.execute(consultas.CREAR, parametros)
        except IntegrityError as error:
            if sqlstate_of(error) == UNIQUE_VIOLATION_SQLSTATE and constraint_of(error) == RESTRICCION_CORREO_UNICO:
                raise CorreoRepetido from error
            raise
        return str(resultado.scalar_one())

    async def asignar_rol(self, usuario_id: str, rol: RolCodigo) -> None:
        await self._connection.execute(consultas.ASIGNAR_ROL, {"usuario_id": usuario_id, "rol": rol.value})

    async def quitar_roles(self, usuario_id: str) -> None:
        await self._connection.execute(consultas.QUITAR_ROLES, {"usuario_id": usuario_id})

    async def cambiar_area(self, usuario_id: str, area_id: int | None) -> None:
        await self._connection.execute(consultas.CAMBIAR_AREA, {"usuario_id": usuario_id, "area_id": area_id})

    async def cambiar_nombre(self, usuario_id: str, nombre_completo: str) -> None:
        await self._connection.execute(
            consultas.CAMBIAR_NOMBRE, {"usuario_id": usuario_id, "nombre_completo": nombre_completo}
        )

    async def cambiar_vigencia(self, usuario_id: str, *, activo: bool, actor: str) -> None:
        await self._connection.execute(
            consultas.CAMBIAR_VIGENCIA, {"usuario_id": usuario_id, "activo": activo, "actor": actor}
        )

    async def cambiar_clave(self, usuario_id: str, huella: str) -> None:
        await self._connection.execute(consultas.CAMBIAR_CLAVE, {"usuario_id": usuario_id, "huella": huella})

    async def cerrar_sesiones(self, usuario_id: str) -> None:
        await self._connection.execute(consultas.CERRAR_SESIONES, {"usuario_id": usuario_id})


class SqlUsuarioUnitOfWork:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def begin(self, actor: str) -> AsyncIterator[SqlUsuarioTransaction]:
        async with transaction(self._engine, actor) as connection:
            yield SqlUsuarioTransaction(connection)
