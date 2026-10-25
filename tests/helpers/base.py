import json
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.shared.transaction import transaction

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

HASHES_DEL_NODO = Path(__file__).parents[1] / "fixtures" / "hashes_argon2_node.json"
CLAVE_DE_PRUEBA = "clave-de-prueba-1"
HUELLA_DE_PRUEBA = next(
    item["hash"] for item in json.loads(HASHES_DEL_NODO.read_text(encoding="utf-8")) if item["clave"] == CLAVE_DE_PRUEBA
)
ACTOR_DE_PRUEBA = "sistema:prueba"
TIPO_ESTABLECIMIENTO = 1
TIPO_OTRANS = 2


async def sembrar_area(engine: AsyncEngine, area_id: int, codigo: str, nombre: str, tipo_area_id: int = 1) -> None:
    async with transaction(engine, ACTOR_DE_PRUEBA) as conexion:
        await conexion.execute(
            text("INSERT INTO catalogo.area (id, codigo, nombre, tipo_area_id) VALUES (:id, :codigo, :nombre, :tipo)"),
            {"id": area_id, "codigo": codigo, "nombre": nombre, "tipo": tipo_area_id},
        )


async def sembrar_usuario(  # noqa: PLR0913
    engine: AsyncEngine,
    correo: str,
    rol: str,
    area_id: int | None,
    *,
    nombre: str = "Persona de Prueba",
    huella: str = HUELLA_DE_PRUEBA,
    activo: bool = True,
) -> str:
    async with transaction(engine, ACTOR_DE_PRUEBA) as conexion:
        identificador = (
            await conexion.execute(
                text(
                    "INSERT INTO gestion.usuario_interno"
                    " (nombre_completo, correo, password_hash, area_id, activo, eliminado_en, eliminado_por)"
                    " VALUES (:nombre, :correo, :huella, :area_id, :activo,"
                    " CASE WHEN :activo THEN NULL ELSE now() END,"
                    " CASE WHEN :activo THEN NULL ELSE CAST(:actor AS text) END) RETURNING id"
                ),
                {
                    "nombre": nombre,
                    "correo": correo,
                    "huella": huella,
                    "area_id": area_id,
                    "activo": activo,
                    "actor": ACTOR_DE_PRUEBA,
                },
            )
        ).scalar_one()
        await conexion.execute(
            text(
                "INSERT INTO gestion.usuario_rol (usuario_interno_id, rol_id)"
                " SELECT :usuario_id, id FROM gestion.rol WHERE codigo = :rol"
            ),
            {"usuario_id": identificador, "rol": rol},
        )
    return str(identificador)


async def consultar(engine: AsyncEngine, sql: str, **parametros: object) -> list[tuple[object, ...]]:
    async with engine.connect() as conexion:
        return [tuple(fila) for fila in (await conexion.execute(text(sql), parametros)).all()]
