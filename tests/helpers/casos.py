import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.shared.transaction import transaction

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

ACTOR_CIUDADANO = "ciudadano:prueba"
ACTOR_IA = "sistema:ia"
ACTOR_OPERADOR = "operador:prueba"
ACTOR_OPERADOR_USUARIO = "usuario:operador-prueba@minsa.gob.pe"
PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
IMAGEN_PNG = f"data:image/png;base64,{PNG_BASE64}"
TIPO_AREA_ESTABLECIMIENTO = "ESTABLECIMIENTO"


@dataclass(frozen=True, slots=True)
class EstablecimientoSembrado:
    establecimiento_id: int
    area_id: int
    area_codigo: str
    area_nombre: str
    codigo_renipress: str
    nombre: str


@dataclass(frozen=True, slots=True)
class CasoSembrado:
    id: str
    codigo: str
    descripcion: str
    evidencias: list[str] = field(default_factory=list)


async def sembrar_establecimiento(
    engine: AsyncEngine, identificador: int, nombre: str = "Establecimiento de Prueba"
) -> EstablecimientoSembrado:
    codigo = str(9_000_000 + identificador)
    area_codigo = f"EESS-{codigo}"
    area_nombre = f"{nombre} {codigo}"
    async with transaction(engine, "sistema:prueba-padron") as conexion:
        area_id = (
            await conexion.execute(
                text(
                    "INSERT INTO catalogo.area (id, codigo, nombre, tipo_area_id)"
                    " SELECT :id, :codigo, :nombre, id FROM catalogo.tipo_area WHERE codigo = :tipo RETURNING id"
                ),
                {"id": identificador, "codigo": area_codigo, "nombre": area_nombre, "tipo": TIPO_AREA_ESTABLECIMIENTO},
            )
        ).scalar_one()
        await conexion.execute(
            text(
                "INSERT INTO catalogo.establecimiento_salud"
                " (id, codigo_renipress, nombre, nivel_atencion_id, categoria, area_id)"
                " VALUES (:id, :renipress, :nombre, 2, 'II-1', :area_id)"
            ),
            {"id": identificador, "renipress": codigo, "nombre": area_nombre, "area_id": area_id},
        )
    return EstablecimientoSembrado(identificador, area_id, area_codigo, area_nombre, codigo, area_nombre)


async def _actuar(engine: AsyncEngine, actor: str, sql: str, **parametros: object) -> None:
    async with transaction(engine, actor) as conexion:
        await conexion.execute(text(sql), parametros)


async def sembrar_caso(  # noqa: PLR0912, PLR0913, PLR0915, C901
    engine: AsyncEngine,
    *,
    categoria: str | None = "RECLAMO",
    confianza: float = 58,
    revision: str | None = None,
    corregida_a: str | None = None,
    establecimiento: EstablecimientoSembrado | None = None,
    destino: EstablecimientoSembrado | None = None,
    estado: str | None = None,
    archivar_motivo: str | None = None,
    anonimo: bool = True,
    nombre: str = "Luis Alberto Quispe",
    dni: str = "00001907",
    rutas_de_evidencias: list[str] | None = None,
    horas_de_edad: int | None = None,
    creado_en: datetime | None = None,
    horas_desde_resolucion: int | None = None,
    marcador: str = "caso de prueba",
) -> CasoSembrado:
    wa_id = f"prueba-wa-{uuid.uuid4()}"
    descripcion = f"{marcador} relato {uuid.uuid4()}"
    async with transaction(engine, ACTOR_CIUDADANO) as conexion:
        usuario_id = (
            await conexion.execute(text("INSERT INTO chatbot.usuario (wa_id) VALUES (:wa) RETURNING id"), {"wa": wa_id})
        ).scalar_one()
        fila = (
            await conexion.execute(
                text(
                    "INSERT INTO chatbot.incidencia_paciente"
                    " (canal_origen_id, usuario_id, wa_id, es_anonimo, dni_reclamante, nombre_reclamante,"
                    "  descripcion, trace_id, establecimiento_id)"
                    " VALUES (1, :usuario_id, :wa_id, :anonimo, :dni, :nombre, :descripcion, :trace_id, :establecimiento)"
                    " RETURNING id, codigo"
                ),
                {
                    "usuario_id": usuario_id,
                    "wa_id": wa_id,
                    "anonimo": anonimo,
                    "dni": None if anonimo else dni,
                    "nombre": None if anonimo else nombre,
                    "descripcion": descripcion,
                    "trace_id": f"prueba-{uuid.uuid4()}",
                    "establecimiento": establecimiento.establecimiento_id if establecimiento else None,
                },
            )
        ).first()
    assert fila is not None
    incidencia_id, codigo = str(fila.id), fila.codigo

    if categoria:
        await _actuar(
            engine,
            ACTOR_IA,
            "UPDATE chatbot.incidencia_paciente"
            " SET categoria_ia_id = (SELECT id FROM catalogo.categoria_incidencia WHERE codigo = :categoria),"
            " categoria_confianza = :confianza, version_clasificador = 'v-prueba' WHERE id = CAST(:id AS uuid)",
            id=incidencia_id,
            categoria=categoria,
            confianza=confianza,
        )
    if revision == "confirmada":
        await _actuar(
            engine,
            ACTOR_OPERADOR,
            "UPDATE chatbot.incidencia_paciente SET categoria_confirmada_en = now() WHERE id = CAST(:id AS uuid)",
            id=incidencia_id,
        )
    elif revision == "corregida":
        await _actuar(
            engine,
            ACTOR_OPERADOR,
            "UPDATE chatbot.incidencia_paciente SET categoria_id ="
            " (SELECT id FROM catalogo.categoria_incidencia WHERE codigo = :nueva) WHERE id = CAST(:id AS uuid)",
            id=incidencia_id,
            nueva=corregida_a,
        )

    area_destino = destino.area_id if destino else None
    area_origen = establecimiento.area_id if establecimiento else None
    previo = (archivar_motivo and "CLASIFICADO") or estado
    if previo in {"DERIVADO", "EN_GESTION"}:
        estado_id = 6 if previo == "DERIVADO" else 3
        await _actuar(
            engine,
            ACTOR_OPERADOR,
            "UPDATE chatbot.incidencia_paciente SET estado_incidencia_id = :estado,"
            " area_destino_id = COALESCE(CAST(:destino AS int), area_destino_id, CAST(:origen AS int))"
            " WHERE id = CAST(:id AS uuid)",
            id=incidencia_id,
            estado=estado_id,
            destino=area_destino,
            origen=area_origen,
        )
    elif previo in {"RESUELTO", "ARCHIVADO"}:
        await _actuar(
            engine,
            ACTOR_OPERADOR,
            "UPDATE chatbot.incidencia_paciente SET medidas_tomadas = 'Se atendió el caso en la prueba.',"
            " fundamento = 'El caso era procedente en la prueba.',"
            " resultado_resolucion_id = (SELECT id FROM catalogo.resultado_resolucion WHERE codigo = 'ATENDIDO')"
            " WHERE id = CAST(:id AS uuid)",
            id=incidencia_id,
        )
        if previo == "ARCHIVADO":
            await _actuar(
                engine,
                "sistema:archivado",
                "UPDATE chatbot.incidencia_paciente SET estado_incidencia_id = 7 WHERE id = CAST(:id AS uuid)",
                id=incidencia_id,
            )
    if archivar_motivo == "VENCIDA_SIN_ATENDER":
        await _actuar(
            engine,
            "sistema:vencimiento",
            "UPDATE chatbot.incidencia_paciente SET estado_incidencia_id = 7 WHERE id = CAST(:id AS uuid)",
            id=incidencia_id,
        )
    elif archivar_motivo:
        await _actuar(
            engine,
            ACTOR_OPERADOR_USUARIO,
            "UPDATE chatbot.incidencia_paciente SET estado_incidencia_id = 7,"
            " motivo_archivo_id = (SELECT id FROM catalogo.motivo_archivo WHERE codigo = :motivo),"
            " archivo_detalle = 'Archivado en la prueba por falta de datos.' WHERE id = CAST(:id AS uuid)",
            id=incidencia_id,
            motivo=archivar_motivo,
        )

    evidencias: list[str] = []
    for indice, ruta in enumerate(rutas_de_evidencias or []):
        async with transaction(engine, ACTOR_CIUDADANO) as conexion:
            evidencia_id = (
                await conexion.execute(
                    text(
                        "INSERT INTO chatbot.evidencia"
                        " (incidencia_paciente_id, tipo_evidencia_id, mime_type, nombre_archivo, tamano, ruta)"
                        " VALUES (CAST(:id AS uuid), 1, 'image/png', :nombre, 2048, :ruta) RETURNING id"
                    ),
                    {"id": incidencia_id, "nombre": f"imagen-{indice + 1}.png", "ruta": ruta},
                )
            ).scalar_one()
        evidencias.append(str(evidencia_id))

    if horas_de_edad is not None or creado_en is not None or horas_desde_resolucion is not None:
        async with engine.begin() as conexion:
            await conexion.execute(text("ALTER TABLE chatbot.incidencia_paciente DISABLE TRIGGER USER"))
            await conexion.execute(
                text(
                    "UPDATE chatbot.incidencia_paciente SET"
                    " fecha_creacion = COALESCE(CAST(:creado AS timestamptz),"
                    " now() - make_interval(hours => CAST(:horas AS int), mins => 1), fecha_creacion),"
                    " resuelto_en = CASE WHEN CAST(:resuelto AS int) IS NULL OR resuelto_en IS NULL THEN resuelto_en"
                    " ELSE now() - make_interval(hours => CAST(:resuelto AS int), mins => 1) END"
                    " WHERE id = CAST(:id AS uuid)"
                ),
                {"id": incidencia_id, "creado": creado_en, "horas": horas_de_edad, "resuelto": horas_desde_resolucion},
            )
            await conexion.execute(text("ALTER TABLE chatbot.incidencia_paciente ENABLE TRIGGER USER"))

    return CasoSembrado(incidencia_id, codigo, descripcion, evidencias)
