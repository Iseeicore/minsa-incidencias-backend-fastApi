from sqlalchemy import text

from app.incidencias.domain.imagen_de_evidencia import LARGO_DEL_INICIO_DE_IMAGEN

EVIDENCIAS = text(
    f"""
    SELECT v.id,
           v.nombre_archivo AS nombre,
           t.codigo AS tipo,
           t.nombre AS tipo_nombre,
           v.fecha_recepcion AS fecha,
           (v.hash_archivo IS NOT NULL) AS verificada,
           (left(v.ruta, {LARGO_DEL_INICIO_DE_IMAGEN}) ~ :inicio) AS contenido_disponible
      FROM chatbot.evidencia v
      JOIN catalogo.tipo_evidencia t ON t.id = v.tipo_evidencia_id
     WHERE v.incidencia_paciente_id = CAST(:incidencia_id AS uuid)
     ORDER BY v.fecha_recepcion, v.id
    """
)
RUTA_DE_EVIDENCIA = text(
    """
    SELECT v.ruta
      FROM chatbot.evidencia v
     WHERE v.incidencia_paciente_id = CAST(:incidencia_id AS uuid) AND v.id = CAST(:evidencia_id AS uuid)
    """
)
HISTORIAL = text(
    """
    SELECT a.operacion,
           a.actor,
           ui.nombre_completo AS actor_nombre,
           a.fecha_hora,
           (a.operacion = 'ACTUALIZACION' AND a.cambios ? 'categoria_ia_id') AS ia,
           (SELECT k.codigo FROM catalogo.categoria_incidencia k
             WHERE k.id = (a.cambios #>> '{categoria_ia_id,despues}')::smallint) AS categoria_ia,
           (a.cambios #>> '{categoria_confianza,despues}')::float8 AS confianza,
           a.cambios #>> '{version_clasificador,despues}' AS version,
           (a.operacion = 'ACTUALIZACION' AND a.cambios ? 'categoria_corregida_en') AS corregida,
           (SELECT k.codigo FROM catalogo.categoria_incidencia k
             WHERE k.id = (a.cambios #>> '{categoria_id,antes}')::smallint) AS categoria_antes,
           (SELECT k.codigo FROM catalogo.categoria_incidencia k
             WHERE k.id = (a.cambios #>> '{categoria_id,despues}')::smallint) AS categoria_despues,
           (a.operacion = 'ACTUALIZACION' AND a.cambios ? 'categoria_confirmada_en') AS confirmada,
           (SELECT s.codigo FROM catalogo.estado_incidencia s
             WHERE s.id = (a.cambios #>> '{estado_incidencia_id,despues}')::smallint) AS estado_nuevo,
           (SELECT ar.nombre FROM catalogo.area ar
             WHERE ar.id = (a.cambios #>> '{area_destino_id,antes}')::bigint) AS area_antes,
           (SELECT ar.nombre FROM catalogo.area ar
             WHERE ar.id = (a.cambios #>> '{area_destino_id,despues}')::bigint) AS area_despues,
           a.cambios #>> '{derivacion_descripcion,despues}' AS descripcion_derivacion,
           (a.operacion = 'ACTUALIZACION' AND a.cambios ? 'medidas_tomadas') AS resolvio,
           (a.operacion = 'ACTUALIZACION' AND a.cambios ? 'reabierto_motivo') AS reabrio
      FROM chatbot.incidencia_paciente_auditoria a
      LEFT JOIN gestion.usuario_interno ui ON a.actor = :prefijo || ui.correo
     WHERE a.incidencia_paciente_id = CAST(:incidencia_id AS uuid)
     ORDER BY a.id
    """
)
