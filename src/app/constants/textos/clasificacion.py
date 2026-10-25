from app.enums.estado_coincidencias import EstadoCoincidencias

EXPLICACION_DE_APOYO = {
    EstadoCoincidencias.NO_CONSULTADA: "No se utilizaron antecedentes para decidir la categoría",
    EstadoCoincidencias.CORROBORADA: (
        "Los antecedentes humanos respaldan la categoría con evidencia en el relato actual"
    ),
    EstadoCoincidencias.SIN_CANDIDATOS: "No hay antecedentes elegibles con semejanza suficiente",
    EstadoCoincidencias.INSUFICIENTE: "La semejanza o la diferencia entre categorías no es suficiente",
    EstadoCoincidencias.CONTRADICTORIA: (
        "Los antecedentes no coinciden con las señales del relato; se conserva la decisión de las reglas"
    ),
}
EXPLICACION_REVISION_REQUERIDA = "Se requiere revisión humana."
EXPLICACION_REVISION_OPCIONAL = "La categoría puede confirmarse o corregirse."
PLANTILLA_DE_EXPLICACION = (
    "Categoría propuesta: {categoria}. Puntaje de reglas de corrupción: {puntaje}. {apoyo}. {revision}"
)
