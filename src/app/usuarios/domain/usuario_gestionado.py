from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UsuarioGestionado:
    id: str
    nombre_completo: str
    correo: str
    activo: bool
    rol: str | None
    area_id: int | None
    area_codigo: str | None
    area_nombre: str | None
