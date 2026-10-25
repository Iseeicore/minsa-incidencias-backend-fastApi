from enum import StrEnum


class OrigenClasificacion(StrEnum):
    REGLAS = "REGLAS"
    REGLAS_CON_APOYO_BD = "REGLAS_CON_APOYO_BD"
    SIN_COINCIDENCIAS = "SIN_COINCIDENCIAS"
