from app.constants.hash import (
    ARGON2_CANONICAL_ORDER,
    ARGON2_PARAM_SEPARATOR,
    ARGON2_PARAMS_INDEX,
    ARGON2_PARTS_SEPARATOR,
)


def canonical_argon2_hash(encoded: str) -> str:
    parts = encoded.split(ARGON2_PARTS_SEPARATOR)
    if len(parts) <= ARGON2_PARAMS_INDEX:
        return encoded
    params = parts[ARGON2_PARAMS_INDEX].split(ARGON2_PARAM_SEPARATOR)
    by_name = dict(param.split("=", 1) for param in params if "=" in param)
    if len(by_name) != len(params) or set(by_name) != set(ARGON2_CANONICAL_ORDER):
        return encoded
    parts[ARGON2_PARAMS_INDEX] = ARGON2_PARAM_SEPARATOR.join(
        f"{name}={by_name[name]}" for name in ARGON2_CANONICAL_ORDER
    )
    return ARGON2_PARTS_SEPARATOR.join(parts)
