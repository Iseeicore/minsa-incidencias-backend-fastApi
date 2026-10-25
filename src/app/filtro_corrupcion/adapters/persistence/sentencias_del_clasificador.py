from sqlalchemy import text

SIGUIENTE_PENDIENTE = text(
    "SELECT i.id, i.codigo, i.descripcion, e.nombre AS establecimiento"
    " FROM chatbot.incidencia_paciente i"
    " JOIN catalogo.estado_incidencia s ON s.id = i.estado_incidencia_id"
    " LEFT JOIN catalogo.establecimiento_salud e ON e.id = i.establecimiento_id"
    " WHERE s.codigo = :estado"
    " AND i.categoria_ia_id IS NULL"
    " AND i.activo"
    " AND NOT (i.id = ANY(CAST(:abandonados AS uuid[])))"
    " AND (CAST(:solo AS uuid[]) IS NULL OR i.id = ANY(CAST(:solo AS uuid[])))"
    " ORDER BY i.fecha_creacion, i.id"
    " LIMIT 1"
    " FOR UPDATE OF i SKIP LOCKED"
)

AREA_MENCIONADA = text("SELECT id FROM catalogo.area WHERE lower(codigo) = lower(:codigo) AND activo LIMIT 1")

INSERTAR_ANALISIS = text(
    "INSERT INTO chatbot.incidencia_analisis"
    " (incidencia_paciente_id, version_reglas, puntaje, senales, cargo_mencionado, area_mencionada_id,"
    " nombre_mencionado)"
    " VALUES (CAST(:incidencia AS uuid), :version_reglas, :puntaje, CAST(:senales AS jsonb), :cargo, :area, :nombre)"
    " ON CONFLICT (incidencia_paciente_id) DO NOTHING"
)

ACTUALIZAR_CATEGORIA = text(
    "UPDATE chatbot.incidencia_paciente"
    " SET categoria_ia_id = (SELECT id FROM catalogo.categoria_incidencia WHERE codigo = :categoria),"
    " categoria_confianza = :confianza,"
    " version_clasificador = :version"
    " WHERE id = CAST(:incidencia AS uuid) AND categoria_ia_id IS NULL"
)

COINCIDENCIAS = text(
    "WITH ejemplos_recientes AS MATERIALIZED ("
    " SELECT c.codigo AS categoria, e.texto_entrenamiento"
    " FROM ia.entrenamiento_categoria e"
    " JOIN chatbot.incidencia_paciente i ON i.id = e.incidencia_paciente_id AND i.activo"
    " JOIN catalogo.categoria_incidencia c ON c.id = e.categoria_final_id AND c.activo"
    " WHERE e.apto_entrenamiento"
    " AND e.incidencia_paciente_id <> CAST(:incidencia AS uuid)"
    " AND c.codigo = ANY(CAST(:categorias AS text[]))"
    " ORDER BY e.fecha_revision DESC, e.id DESC"
    " LIMIT CAST(:ejemplos AS int)"
    "), coincidencias AS ("
    " SELECT e.categoria,"
    " CAST(public.similarity(public.f_unaccent(e.texto_entrenamiento),"
    " public.f_unaccent(CAST(:texto AS text))) AS float8) AS similitud"
    " FROM ejemplos_recientes e"
    ")"
    " SELECT categoria, CAST(max(similitud) AS float8) AS similitud"
    " FROM coincidencias"
    " WHERE similitud >= CAST(:minima AS float8)"
    " GROUP BY categoria"
    " ORDER BY similitud DESC, categoria ASC"
    " LIMIT CAST(:maximo AS int)"
)

ALARMA_SIN_CLASIFICAR = text(
    "SELECT CAST(count(*) AS int) AS atrasados,"
    " CAST(round(CAST(extract(epoch FROM (now() - min(i.fecha_creacion))) / 60 AS numeric), 1) AS float8) AS minutos,"
    " (array_agg(i.codigo ORDER BY i.fecha_creacion, i.id))[1:CAST(:maximo AS int)] AS codigos"
    " FROM chatbot.incidencia_paciente i"
    " JOIN catalogo.estado_incidencia s ON s.id = i.estado_incidencia_id"
    " WHERE s.codigo = :estado"
    " AND i.categoria_ia_id IS NULL"
    " AND i.activo"
    " AND i.fecha_creacion < now() - make_interval(mins => CAST(:minutos AS int))"
)
