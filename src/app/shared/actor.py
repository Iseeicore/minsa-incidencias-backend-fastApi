from app.constants.actores import ACTOR_USUARIO_INTERNO_PREFIX


def actor_usuario_interno(correo: str) -> str:
    return f"{ACTOR_USUARIO_INTERNO_PREFIX}{correo}"
