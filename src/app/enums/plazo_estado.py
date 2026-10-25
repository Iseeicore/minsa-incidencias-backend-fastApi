from enum import StrEnum


class PlazoEstado(StrEnum):
    EN_PLAZO = "en-plazo"
    POR_VENCER = "por-vencer"
    VENCIDO = "vencido"
