from sqlalchemy import text

COLUMNAS_DE_USUARIO = """
    SELECT u.id,
           u.nombre_completo,
           u.correo,
           u.activo,
           (SELECT r.codigo
              FROM gestion.usuario_rol ur
              JOIN gestion.rol r ON r.id = ur.rol_id AND r.activo
             WHERE ur.usuario_interno_id = u.id
             ORDER BY r.codigo
             LIMIT 1) AS rol,
           u.area_id,
           a.codigo AS area_codigo,
           a.nombre AS area_nombre
      FROM gestion.usuario_interno u
      LEFT JOIN catalogo.area a ON a.id = u.area_id
"""
LISTAR = text(
    COLUMNAS_DE_USUARIO
    + r"""
     WHERE (NOT :filtrar_area OR u.area_id = CAST(:solo_area_id AS int))
       AND (CAST(:area_codigo AS text) IS NULL OR a.codigo = CAST(:area_codigo AS text))
       AND (CAST(:patron AS text) IS NULL
            OR public.f_unaccent(lower(u.nombre_completo))
               LIKE public.f_unaccent(lower(CAST(:patron AS text))) ESCAPE '\'
            OR u.correo LIKE lower(CAST(:patron AS text)) ESCAPE '\')
       AND (NOT :hay_cursor OR (u.nombre_completo, u.id) > (CAST(:cursor_nombre AS text), CAST(:cursor_id AS uuid)))
     ORDER BY u.nombre_completo, u.id
     LIMIT :limite
    """
)
BUSCAR_POR_ID = text(
    COLUMNAS_DE_USUARIO
    + """
     WHERE u.id = CAST(:usuario_id AS uuid)
       AND (NOT :filtrar_area OR u.area_id = CAST(:solo_area_id AS int))
    """
)
BUSCAR_POR_ID_BLOQUEANDO = text(
    COLUMNAS_DE_USUARIO
    + """
     WHERE u.id = CAST(:usuario_id AS uuid)
       AND (NOT :filtrar_area OR u.area_id = CAST(:solo_area_id AS int))
       FOR UPDATE OF u
    """
)
AREA_ACTIVA = text("SELECT id FROM catalogo.area WHERE codigo = :codigo AND activo")
CREAR = text(
    """
    INSERT INTO gestion.usuario_interno (nombre_completo, correo, password_hash, area_id)
    VALUES (:nombre_completo, :correo, :huella, CAST(:area_id AS int))
    RETURNING id
    """
)
ASIGNAR_ROL = text(
    """
    INSERT INTO gestion.usuario_rol (usuario_interno_id, rol_id)
    SELECT CAST(:usuario_id AS uuid), id FROM gestion.rol WHERE codigo = :rol
    """
)
QUITAR_ROLES = text("DELETE FROM gestion.usuario_rol WHERE usuario_interno_id = CAST(:usuario_id AS uuid)")
CAMBIAR_AREA = text(
    "UPDATE gestion.usuario_interno SET area_id = CAST(:area_id AS int) WHERE id = CAST(:usuario_id AS uuid)"
)
CAMBIAR_NOMBRE = text(
    "UPDATE gestion.usuario_interno SET nombre_completo = :nombre_completo WHERE id = CAST(:usuario_id AS uuid)"
)
CAMBIAR_VIGENCIA = text(
    """
    UPDATE gestion.usuario_interno
       SET activo = CAST(:activo AS boolean),
           eliminado_en = CASE WHEN CAST(:activo AS boolean) THEN NULL ELSE now() END,
           eliminado_por = CASE WHEN CAST(:activo AS boolean) THEN NULL ELSE CAST(:actor AS text) END
     WHERE id = CAST(:usuario_id AS uuid)
    """
)
CAMBIAR_CLAVE = text("UPDATE gestion.usuario_interno SET password_hash = :huella WHERE id = CAST(:usuario_id AS uuid)")
CERRAR_SESIONES = text(
    """
    UPDATE gestion.sesion_usuario SET revocada_en = now()
     WHERE usuario_interno_id = CAST(:usuario_id AS uuid) AND revocada_en IS NULL
    """
)
