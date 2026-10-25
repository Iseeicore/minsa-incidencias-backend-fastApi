from enum import StrEnum


class EstadoIncidencia(StrEnum):
    REGISTRADO = "REGISTRADO"
    CLASIFICADO = "CLASIFICADO"
    DERIVADO = "DERIVADO"
    EN_GESTION = "EN_GESTION"
    RESUELTO = "RESUELTO"
    ARCHIVADO = "ARCHIVADO"
