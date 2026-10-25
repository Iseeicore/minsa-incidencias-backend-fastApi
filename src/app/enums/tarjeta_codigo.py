from enum import StrEnum


class TarjetaCodigo(StrEnum):
    RECIBIDOS = "recibidos"
    PENDIENTES = "pendientes"
    EN_GESTION = "en-gestion"
    POR_VENCER = "por-vencer"
    VENCIDOS = "vencidos"
    RESUELTOS = "resueltos"
    SIN_CLASIFICAR = "sin-clasificar"
    POR_REVISAR = "por-revisar"
    SIN_TOMAR = "sin-tomar"
    CORREGIDAS_A_CORRUPCION = "corregidas-a-corrupcion"
