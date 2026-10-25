CASO_EJEMPLO = {
    "codigo": "MINSA-2026-000001",
    "categoria": "reclamo",
    "categoriaIa": "reclamo",
    "confianzaIa": 58,
    "etiquetas": [],
    "prioridad": None,
    "organismo": None,
    "area": {"codigo": "HOSP-01", "nombre": "Hospital Uno"},
    "establecimiento": {
        "codigoRenipress": "1234",
        "nombre": "Hospital Uno",
        "nivelAtencion": "II",
        "categoria": "II-1",
    },
    "responsable": None,
    "estado": "clasificado",
    "horasDesdeLlegada": 5,
    "horasDesdeResolucion": None,
    "revisadoPorHumano": False,
    "corregida": False,
    "plazo": {"tipo": "atencion", "estado": "en-plazo", "venceEn": "2026-11-23T12:00:00.000Z", "horasRestantes": 720},
    "acciones": ["confirmar", "corregir"],
}
DETALLE_EJEMPLO = {
    **CASO_EJEMPLO,
    "descripcionDerivacion": None,
    "resolucion": None,
    "archivo": None,
    "reapertura": None,
    "descripcion": "Relato del caso.",
    "reclamante": "Anónimo",
    "evidencias": [],
    "historial": [
        {
            "titulo": "Recibido por WhatsApp",
            "detalle": "Registrado como incidencia.",
            "hora": "hace 5 h",
            "fecha": "2026-10-24T07:00:00.000Z",
        }
    ],
}
DERIVACION_EJEMPLO = {
    "id": "4821",
    "codigoCaso": "MINSA-2026-000001",
    "fechaDerivacion": "2026-01-15T14:30:00.000Z",
    "origen": {"codigo": "OTRANS", "nombre": "Oficina de Transparencia Ejemplo"},
    "destino": {"codigo": "EESS-0001", "nombre": "Centro de Salud Ejemplo", "codigoRenipress": "1"},
    "derivadoPor": "Lucía Ramos Prueba",
    "descripcion": "Se devuelve al establecimiento porque corresponde a un reclamo.",
    "categoria": "reclamo",
    "estado": "derivado",
    "motivoArchivo": None,
}
