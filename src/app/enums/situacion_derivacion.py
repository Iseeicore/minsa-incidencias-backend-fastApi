from enum import StrEnum


class SituacionDerivacion(StrEnum):
    PENDIENTE = "pendiente"
    EN_GESTION = "en-gestion"
    RESUELTO = "resuelto"
    ARCHIVADO = "archivado"
