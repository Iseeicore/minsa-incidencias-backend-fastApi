from typing import TYPE_CHECKING

from app.constants.incidencias import (
    ACTOR_PREFIJO_SISTEMA,
    ACTOR_PREFIJO_USUARIO,
    ESTADOS_ABIERTOS,
    ZONA_DE_LIMA,
)
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.tipo_area import TipoArea
from app.shared.text_search import like_pattern

if TYPE_CHECKING:
    from app.incidencias.domain.consultas import FiltrosCasos, VisibilidadOperativa
    from app.shared.permisos import ReglaDeAccion
    from app.shared.sql_params import ParametrosSql

TIPOS_DE_AREA_SIN_SENSIBLES = (TipoArea.ESTABLECIMIENTO.value, TipoArea.DIRIS.value)
ESTADOS_CONOCIDOS = [estado.value for estado in EstadoIncidencia]
INICIO_DEL_PLAZO = "COALESCE(i.reabierto_en, i.fecha_creacion)"
VENCE_LA_ATENCION = f"catalogo.sumar_dias_habiles({INICIO_DEL_PLAZO}, c.plazo_dias_habiles)"
VENCE_LA_ATENCION_EN_MS = f"date_trunc('milliseconds', {VENCE_LA_ATENCION})"
DESDE_BASICO = """
  FROM chatbot.incidencia_paciente i
  JOIN catalogo.estado_incidencia e ON e.id = i.estado_incidencia_id
  LEFT JOIN catalogo.categoria_incidencia c ON c.id = i.categoria_id"""
ESTADOS_ABIERTOS_VALORES = [estado.value for estado in ESTADOS_ABIERTOS]
ESCAPE_DE_LIKE = "ESCAPE '\\'"


def visibilidad(p: ParametrosSql, visible: VisibilidadOperativa) -> str:
    roles = p.con_tipo(list(visible.roles), "text[]")
    sin_categoria = p.con_tipo(visible.ver_sin_categoria, "boolean")
    area = p.con_tipo(visible.area_id, "int")
    tipos_sin_sensibles = p.con_tipo(list(TIPOS_DE_AREA_SIN_SENSIBLES), "text[]")
    return f"""(
    (i.categoria_id IS NOT NULL AND EXISTS (
       SELECT 1 FROM gestion.rol_categoria rc
         JOIN gestion.rol r ON r.id = rc.rol_id AND r.activo
         JOIN catalogo.categoria_incidencia k ON k.id = rc.categoria_incidencia_id
         LEFT JOIN catalogo.tipo_area ta ON ta.id = r.tipo_area_id
        WHERE r.codigo = ANY({roles}) AND rc.categoria_incidencia_id = i.categoria_id
          AND (r.tipo_area_id IS NULL OR i.area_destino_id = {area})
          AND NOT (k.es_sensible AND COALESCE(ta.codigo = ANY({tipos_sin_sensibles}), false))))
    OR (i.categoria_id IS NULL AND {sin_categoria})
  )"""


def condiciones_base(p: ParametrosSql, visible: VisibilidadOperativa) -> list[str]:
    return ["i.activo", f"e.codigo = ANY({p.con_tipo(ESTADOS_CONOCIDOS, 'text[]')})", visibilidad(p, visible)]


def condiciones_por_vencer(p: ParametrosSql, aviso_horas: int, *, sin_vencidos: bool = False) -> list[str]:
    abiertos = p.con_tipo(ESTADOS_ABIERTOS_VALORES, "text[]")
    horas = p.con_tipo(aviso_horas, "int")
    condiciones = [
        f"e.codigo = ANY({abiertos})",
        f"{VENCE_LA_ATENCION} <= now() + make_interval(hours => {horas})",
    ]
    if sin_vencidos:
        condiciones.append(f"{VENCE_LA_ATENCION} > now()")
    return condiciones


def _condiciones_de_catalogo(p: ParametrosSql, filtros: FiltrosCasos) -> list[str]:
    condiciones: list[str] = []
    if filtros.establecimiento:
        renipress = p.agregar(filtros.establecimiento)
        condiciones.append(
            "i.establecimiento_id = "
            f"(SELECT f.id FROM catalogo.establecimiento_salud f WHERE f.codigo_renipress = {renipress})"
        )
    if filtros.estado:
        condiciones.append(f"e.codigo = {p.agregar(filtros.estado.value)}")
    if filtros.motivo_archivo:
        motivo = p.agregar(filtros.motivo_archivo.value)
        condiciones.append(
            f"i.motivo_archivo_id = (SELECT m.id FROM catalogo.motivo_archivo m WHERE m.codigo = {motivo})"
        )
    if filtros.categoria:
        condiciones.append(f"c.codigo = {p.agregar(filtros.categoria.value)}")
    if filtros.sin_categoria:
        condiciones.append("i.categoria_id IS NULL")
    return condiciones


def _condiciones_de_tiempo_y_texto(p: ParametrosSql, filtros: FiltrosCasos) -> list[str]:
    condiciones: list[str] = []
    if filtros.desde:
        desde = p.con_tipo(filtros.desde, "date")
        condiciones.append(f"i.fecha_creacion >= ({desde})::timestamp AT TIME ZONE '{ZONA_DE_LIMA}'")
    if filtros.hasta:
        hasta = p.con_tipo(filtros.hasta, "date")
        condiciones.append(f"i.fecha_creacion < (({hasta}) + 1)::timestamp AT TIME ZONE '{ZONA_DE_LIMA}'")
    if filtros.aviso_horas is not None:
        condiciones.extend(condiciones_por_vencer(p, filtros.aviso_horas, sin_vencidos=True))
    if filtros.texto:
        patron = p.agregar(like_pattern(filtros.texto))
        coincide_codigo = f"i.codigo ILIKE {patron} {ESCAPE_DE_LIKE}"
        coincide_relato = f"i.descripcion ILIKE {patron} {ESCAPE_DE_LIKE}"
        condiciones.append(f"({coincide_codigo} OR {coincide_relato})")
    return condiciones


def condiciones_de_filtros(p: ParametrosSql, filtros: FiltrosCasos) -> list[str]:
    return [*_condiciones_de_catalogo(p, filtros), *_condiciones_de_tiempo_y_texto(p, filtros)]


def condicion_de_pendientes(p: ParametrosSql, reglas: tuple[ReglaDeAccion, ...] | None) -> list[str]:
    if reglas is None:
        return []
    if not reglas:
        return ["false"]
    alternativas: list[str] = []
    for regla in reglas:
        estados = p.con_tipo([estado.value for estado in regla.estados], "text[]")
        partes = [f"e.codigo = ANY({estados})"]
        if regla.categorias:
            categorias = p.con_tipo([categoria.value for categoria in regla.categorias], "text[]")
            partes.append(f"c.codigo = ANY({categorias})")
        if regla.revisada is not None:
            revisada = p.con_tipo(regla.revisada, "boolean")
            partes.append(
                f"(i.categoria_corregida_en IS NOT NULL OR i.categoria_confirmada_en IS NOT NULL) = {revisada}"
            )
        alternativas.append(f"({' AND '.join(partes)})")
    return [f"({' OR '.join(alternativas)})"]


def consulta_de_caso(p: ParametrosSql) -> str:
    derivado = p.agregar(EstadoIncidencia.DERIVADO.value)
    prefijo_usuario = p.agregar(ACTOR_PREFIJO_USUARIO)
    prefijo_sistema = p.agregar(ACTOR_PREFIJO_SISTEMA)
    return f"""
    SELECT i.id,
           i.codigo,
           e.codigo AS estado,
           c.codigo AS categoria,
           cia.codigo AS categoria_ia,
           i.categoria_confianza::float8 AS confianza_ia,
           i.fecha_creacion,
           i.resuelto_en,
           now() AS ahora,
           (i.categoria_corregida_en IS NOT NULL OR i.categoria_confirmada_en IS NOT NULL) AS revisada,
           (i.categoria_corregida_en IS NOT NULL) AS corregida,
           ad.codigo AS area_codigo,
           ad.nombre AS area_nombre,
           i.area_destino_id,
           es.area_id AS area_origen_id,
           es.codigo_renipress AS establecimiento_codigo,
           es.nombre AS establecimiento_nombre,
           na.codigo AS establecimiento_nivel,
           es.categoria AS establecimiento_categoria,
           CASE WHEN ui.id IS NOT NULL THEN ui.nombre_completo
                WHEN starts_with(resp.actor, {prefijo_sistema}) THEN 'Sistema'
           END AS responsable,
           i.medidas_tomadas,
           i.fundamento,
           rr.codigo AS resultado_resolucion,
           ma.codigo AS motivo_archivo,
           i.archivo_detalle,
           i.archivado_en,
           i.reabierto_en,
           i.reabierto_motivo,
           {VENCE_LA_ATENCION} AS vence_atencion_en,
           i.derivacion_descripcion AS descripcion_derivacion,
           i.descripcion,
           i.es_anonimo,
           i.dni_reclamante AS dni,
           i.nombre_reclamante AS nombre,
           co.nombre AS canal,
           COALESCE(c.es_sensible, false) AS sensible
      FROM chatbot.incidencia_paciente i
      JOIN catalogo.estado_incidencia e ON e.id = i.estado_incidencia_id
      JOIN catalogo.canal_origen co ON co.id = i.canal_origen_id
      LEFT JOIN catalogo.categoria_incidencia c ON c.id = i.categoria_id
      LEFT JOIN catalogo.categoria_incidencia cia ON cia.id = i.categoria_ia_id
      LEFT JOIN catalogo.area ad ON ad.id = i.area_destino_id
      LEFT JOIN catalogo.establecimiento_salud es ON es.id = i.establecimiento_id
      LEFT JOIN catalogo.nivel_atencion na ON na.id = es.nivel_atencion_id
      LEFT JOIN catalogo.resultado_resolucion rr ON rr.id = i.resultado_resolucion_id
      LEFT JOIN catalogo.motivo_archivo ma ON ma.id = i.motivo_archivo_id
      LEFT JOIN LATERAL (
        SELECT COALESCE(
                 (SELECT a.actor
                    FROM chatbot.incidencia_paciente_auditoria a
                   WHERE a.incidencia_paciente_id = i.id
                     AND a.operacion = 'ACTUALIZACION'
                     AND a.cambios #>> '{{estado_incidencia_id,despues}}'
                         = (SELECT d.id::text FROM catalogo.estado_incidencia d WHERE d.codigo = {derivado})
                   ORDER BY a.id DESC LIMIT 1),
                 i.categoria_corregida_por,
                 i.categoria_confirmada_por) AS actor
      ) resp ON true
      LEFT JOIN gestion.usuario_interno ui ON resp.actor = {prefijo_usuario} || ui.correo"""
