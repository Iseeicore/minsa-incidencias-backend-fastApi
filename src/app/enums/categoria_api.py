from enum import StrEnum


class CategoriaApi(StrEnum):
    DENUNCIA_CORRUPCION = "denuncia-corrupcion"
    QUEJA = "queja"
    RECLAMO = "reclamo"
    OTRO = "otro"
