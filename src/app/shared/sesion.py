from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SesionActual:
    sesion_id: str
    usuario_id: str
    correo: str
    nombre_completo: str
    roles: tuple[str, ...]
