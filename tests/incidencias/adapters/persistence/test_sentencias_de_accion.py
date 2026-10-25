import pytest

from app.incidencias.adapters.persistence import sentencias_de_accion

ESCRITURAS = [
    (sentencias_de_accion.CONFIRMAR, "categoria_confirmada_en = now()"),
    (sentencias_de_accion.CORREGIR, "COALESCE(CAST(:descripcion AS text), derivacion_descripcion)"),
    (sentencias_de_accion.DERIVAR, "area_destino_id = CAST(:area_id AS bigint)"),
    (sentencias_de_accion.CAMBIAR_ESTADO, "estado_incidencia_id"),
    (sentencias_de_accion.RESOLVER, "resultado_resolucion_id"),
    (sentencias_de_accion.ARCHIVAR, "motivo_archivo_id"),
    (sentencias_de_accion.REABRIR, "reabierto_motivo = :motivo"),
]


@pytest.mark.parametrize(("sentencia", "fragmento"), ESCRITURAS)
def test_cada_escritura_actualiza_un_solo_caso_por_su_identificador(sentencia: object, fragmento: str) -> None:
    sql = str(sentencia)

    assert sql.lstrip().startswith("UPDATE chatbot.incidencia_paciente")
    assert fragmento in sql
    assert "WHERE id = CAST(:incidencia_id AS uuid)" in sql


@pytest.mark.parametrize(
    ("sentencia", "criterio"),
    [
        (sentencias_de_accion.AREA_RECEPTORA_POR_ID, "a.id = CAST(:area_id AS bigint)"),
        (sentencias_de_accion.AREA_RECEPTORA_POR_CODIGO, "a.codigo = :codigo"),
    ],
)
def test_el_area_receptora_exige_area_y_tipo_activos_y_establecimiento_activo(sentencia: object, criterio: str) -> None:
    sql = str(sentencia)

    assert criterio in sql
    assert "a.activo" in sql
    assert "ta.activo" in sql
    assert "catalogo.establecimiento_salud" in sql
    assert ":tipo" in sql
    assert ":establecimiento" in sql
