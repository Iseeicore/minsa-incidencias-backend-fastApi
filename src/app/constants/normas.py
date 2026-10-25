from app.constants.normas_ayuda_memoria import FRAGMENTOS_DE_LA_AYUDA_MEMORIA
from app.constants.normas_directiva import FRAGMENTOS_DE_LA_DIRECTIVA

ETIQUETA_REFERENCIA_ORIENTATIVA = "Referencia orientativa; la califica OTRANS."
VERSION_DE_NORMAS = "normas-v1"
AVISO_DE_NORMAS = (
    "Fragmentos de normas para la trazabilidad del análisis (RAG fase 1). Son una referencia orientativa: la "
    "calificación la hace OTRANS."
)
TRANSCRIPCION_ANEXO_C_COTEJADA = False
AVISO_DE_TRANSCRIPCION = (
    "El Anexo C (20 supuestos) se transcribió a ojo desde las dos imágenes EMF del Word «Supuestos "
    "establecidos en la norma.docx», sin OCR, y no se ha cotejado con el documento oficial de la PCM. Sí se "
    "comparó con un segundo texto que pegó el usuario (ver cotejoConTextoDelUsuario). Los fragmentos de la "
    "ayuda memoria salen del texto del Word, párrafo por párrafo, con sus erratas."
)
COTEJO_FECHA = "2026-10-09"
COTEJO_COMPARADOS = 20
COTEJO_COINCIDEN_LITERALMENTE = 18
COTEJO_DIFIEREN_SOLO_EN_MAYUSCULAS = ("ANEXO_C-III-e", "ANEXO_C-III-g")
COTEJO_NOTA = (
    "El usuario pegó el Anexo C como texto. 18 de 20 supuestos son idénticos palabra por palabra; III-e y "
    "III-g difieren solo en mayúsculas (la imagen trae «Enriquecimiento Ilícito» y «Negociación Incompatible»; "
    "el texto pegado, en minúscula) y se conserva la versión de la imagen. Son dos transcripciones sin el "
    "documento oficial a la vista: no sustituyen el cotejo con la PCM."
)
FUENTES_DE_NORMAS: tuple[dict[str, str], ...] = (
    {
        "id": "DIRECTIVA_002_2023_PCM_SIP",
        "nombre": (
            "Directiva N° 002-2023-PCM-SIP, Directiva para la gestión de denuncias y solicitudes de medidas de "
            "protección al denunciante de actos de corrupción recibidas a través de la Plataforma Digital "
            "Única de Denuncias del Ciudadano, aprobada por Resolución de Secretaría de Integridad Pública N° "
            "005-2023-PCM-SIP (Anexo C)"
        ),
        "archivo": "Supuestos establecidos en la norma.docx",
    },
    {
        "id": "AYUDA_MEMORIA_OTRANS",
        "nombre": "AYUDA MEMORIA, Oficina de Transparencia y Anticorrupción (OTRANS) del MINSA",
        "archivo": "AYUDA MEMORIA.docx",
    },
)
FRAGMENTOS_DE_NORMAS = (*FRAGMENTOS_DE_LA_DIRECTIVA, *FRAGMENTOS_DE_LA_AYUDA_MEMORIA)
