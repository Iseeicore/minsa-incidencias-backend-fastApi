from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UsuarioInterno:
    id: str
    correo: str
    nombre_completo: str
    password_hash: str
    activo: bool
