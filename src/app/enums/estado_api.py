from enum import StrEnum


class EstadoApi(StrEnum):
    REGISTRADO = "registrado"
    CLASIFICADO = "clasificado"
    DERIVADO = "derivado"
    EN_GESTION = "en-gestion"
    RESUELTO = "resuelto"
    ARCHIVADO = "archivado"
