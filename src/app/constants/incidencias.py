from app.enums.categoria_api import CategoriaApi
from app.enums.categoria_incidencia import CategoriaIncidencia

CATEGORIA_API: dict[CategoriaIncidencia, CategoriaApi] = {
    CategoriaIncidencia.DENUNCIA_CORRUPCION: CategoriaApi.DENUNCIA_CORRUPCION,
    CategoriaIncidencia.QUEJA: CategoriaApi.QUEJA,
    CategoriaIncidencia.RECLAMO: CategoriaApi.RECLAMO,
    CategoriaIncidencia.OTRO: CategoriaApi.OTRO,
}
AREA_CODIGO_LONGITUD_MAXIMA = 50
TEXTO_BUSQUEDA_MAXIMO = 100
