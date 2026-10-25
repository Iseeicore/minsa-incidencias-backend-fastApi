from sqlalchemy import text

CONFIRMAR = text(
    """
    UPDATE chatbot.incidencia_paciente
       SET categoria_confirmada_en = now()
     WHERE id = CAST(:incidencia_id AS uuid)
    """
)
CORREGIR = text(
    """
    UPDATE chatbot.incidencia_paciente
       SET categoria_id = (SELECT k.id FROM catalogo.categoria_incidencia k WHERE k.codigo = :categoria AND k.activo),
           derivacion_descripcion = COALESCE(CAST(:descripcion AS text), derivacion_descripcion)
     WHERE id = CAST(:incidencia_id AS uuid)
    """
)
DERIVAR = text(
    """
    UPDATE chatbot.incidencia_paciente
       SET estado_incidencia_id = (SELECT s.id FROM catalogo.estado_incidencia s WHERE s.codigo = :estado),
           area_destino_id = CAST(:area_id AS bigint),
           derivacion_descripcion = :descripcion
     WHERE id = CAST(:incidencia_id AS uuid)
    """
)
CAMBIAR_ESTADO = text(
    """
    UPDATE chatbot.incidencia_paciente
       SET estado_incidencia_id = (SELECT s.id FROM catalogo.estado_incidencia s WHERE s.codigo = :estado)
     WHERE id = CAST(:incidencia_id AS uuid)
    """
)
RESOLVER = text(
    """
    UPDATE chatbot.incidencia_paciente
       SET medidas_tomadas = :medidas_tomadas,
           fundamento = :fundamento,
           resultado_resolucion_id = (SELECT r.id FROM catalogo.resultado_resolucion r WHERE r.codigo = :resultado)
     WHERE id = CAST(:incidencia_id AS uuid)
    """
)
ARCHIVAR = text(
    """
    UPDATE chatbot.incidencia_paciente
       SET estado_incidencia_id = (SELECT s.id FROM catalogo.estado_incidencia s WHERE s.codigo = :estado),
           motivo_archivo_id = (SELECT m.id FROM catalogo.motivo_archivo m WHERE m.codigo = :motivo),
           archivo_detalle = :detalle
     WHERE id = CAST(:incidencia_id AS uuid)
    """
)
REABRIR = text(
    """
    UPDATE chatbot.incidencia_paciente
       SET estado_incidencia_id = (SELECT s.id FROM catalogo.estado_incidencia s WHERE s.codigo = :estado),
           reabierto_motivo = :motivo
     WHERE id = CAST(:incidencia_id AS uuid)
    """
)
AREA_RECEPTORA_POR_ID = text(
    """
    SELECT a.id
      FROM catalogo.area a
      JOIN catalogo.tipo_area ta ON ta.id = a.tipo_area_id AND ta.activo
     WHERE a.id = CAST(:area_id AS bigint) AND a.activo AND ta.codigo = :tipo
       AND (ta.codigo <> :establecimiento OR EXISTS (
         SELECT 1 FROM catalogo.establecimiento_salud es WHERE es.area_id = a.id AND es.activo))
    """
)
AREA_RECEPTORA_POR_CODIGO = text(
    """
    SELECT a.id
      FROM catalogo.area a
      JOIN catalogo.tipo_area ta ON ta.id = a.tipo_area_id AND ta.activo
     WHERE a.codigo = :codigo AND a.activo AND ta.codigo = :tipo
       AND (ta.codigo <> :establecimiento OR EXISTS (
         SELECT 1 FROM catalogo.establecimiento_salud es WHERE es.area_id = a.id AND es.activo))
    """
)
