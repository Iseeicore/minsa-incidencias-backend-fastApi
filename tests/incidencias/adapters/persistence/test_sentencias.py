from app.incidencias.adapters.persistence import sentencias


def test_las_evidencias_se_ordenan_y_marcan_si_su_contenido_es_una_imagen_permitida() -> None:
    sql = str(sentencias.EVIDENCIAS)

    assert "chatbot.evidencia" in sql
    assert "contenido_disponible" in sql
    assert "ORDER BY v.fecha_recepcion, v.id" in sql
    assert ":inicio" in sql


def test_la_ruta_de_una_evidencia_se_busca_por_caso_y_por_evidencia() -> None:
    sql = str(sentencias.RUTA_DE_EVIDENCIA)

    assert ":incidencia_id" in sql
    assert ":evidencia_id" in sql


def test_el_historial_sale_de_la_auditoria_en_orden_de_registro() -> None:
    sql = str(sentencias.HISTORIAL)

    assert "chatbot.incidencia_paciente_auditoria" in sql
    assert "ORDER BY a.id" in sql
    assert ":prefijo" in sql
