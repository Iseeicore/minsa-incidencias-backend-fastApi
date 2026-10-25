from enum import StrEnum


class MotivoDeCierre(StrEnum):
    CLIENTE = "cliente"
    SESION_INVALIDA = "sesion-invalida"
    APAGADO = "apagado"
