from enum import StrEnum


class CategoriaFiltro(StrEnum):
    DENUNCIA_CORRUPCION = "denuncia-corrupcion"
    QUEJA = "queja"
    RECLAMO = "reclamo"
    OTRO = "otro"
    SIN_CATEGORIA = "sin-categoria"
