from app.enums.categoria_api import CategoriaApi
from app.enums.categoria_incidencia import CategoriaIncidencia

CATEGORIA_API: dict[CategoriaIncidencia, CategoriaApi] = {
    CategoriaIncidencia.DENUNCIA_CORRUPCION: CategoriaApi.DENUNCIA_CORRUPCION,
    CategoriaIncidencia.QUEJA: CategoriaApi.QUEJA,
    CategoriaIncidencia.RECLAMO: CategoriaApi.RECLAMO,
    CategoriaIncidencia.OTRO: CategoriaApi.OTRO,
}
