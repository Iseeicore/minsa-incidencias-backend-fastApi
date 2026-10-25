import secrets

from app.constants.usuarios import CLAVE_INICIAL_ALFABETO, CLAVE_INICIAL_LONGITUD


def generar_clave_inicial(longitud: int = CLAVE_INICIAL_LONGITUD, alfabeto: str = CLAVE_INICIAL_ALFABETO) -> str:
    return "".join(secrets.choice(alfabeto) for _ in range(longitud))
