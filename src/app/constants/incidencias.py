from app.enums.categoria_api import CategoriaApi
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_api import EstadoApi
from app.enums.estado_incidencia import EstadoIncidencia

CATEGORIA_API: dict[CategoriaIncidencia, CategoriaApi] = {
    CategoriaIncidencia.DENUNCIA_CORRUPCION: CategoriaApi.DENUNCIA_CORRUPCION,
    CategoriaIncidencia.QUEJA: CategoriaApi.QUEJA,
    CategoriaIncidencia.RECLAMO: CategoriaApi.RECLAMO,
    CategoriaIncidencia.OTRO: CategoriaApi.OTRO,
}
CATEGORIA_DESDE_API: dict[CategoriaApi, CategoriaIncidencia] = {api: base for base, api in CATEGORIA_API.items()}
CATEGORIA_ETIQUETA: dict[CategoriaIncidencia, str] = {
    CategoriaIncidencia.DENUNCIA_CORRUPCION: "Denuncia por corrupción",
    CategoriaIncidencia.QUEJA: "Queja",
    CategoriaIncidencia.RECLAMO: "Reclamo",
    CategoriaIncidencia.OTRO: "Otro",
}
ESTADO_API: dict[EstadoIncidencia, EstadoApi] = {
    EstadoIncidencia.REGISTRADO: EstadoApi.REGISTRADO,
    EstadoIncidencia.CLASIFICADO: EstadoApi.CLASIFICADO,
    EstadoIncidencia.DERIVADO: EstadoApi.DERIVADO,
    EstadoIncidencia.EN_GESTION: EstadoApi.EN_GESTION,
    EstadoIncidencia.RESUELTO: EstadoApi.RESUELTO,
    EstadoIncidencia.ARCHIVADO: EstadoApi.ARCHIVADO,
}
ESTADO_DESDE_API: dict[EstadoApi, EstadoIncidencia] = {api: base for base, api in ESTADO_API.items()}
ESTADOS_ABIERTOS = (
    EstadoIncidencia.REGISTRADO,
    EstadoIncidencia.CLASIFICADO,
    EstadoIncidencia.DERIVADO,
    EstadoIncidencia.EN_GESTION,
)

AREA_CODIGO_LONGITUD_MAXIMA = 50
TEXTO_BUSQUEDA_MAXIMO = 100
LISTADO_LIMITE_POR_DEFECTO = 20
LISTADO_LIMITE_MAXIMO = 100
CURSOR_LONGITUD_MAXIMA = 200
LISTADO_RANGO_MAXIMO_DIAS = 366
CONTEO_TOPE = 1000
POR_VENCER_LISTA_MAXIMA = 10
MILISEGUNDOS_POR_HORA = 3_600_000
SEGUNDOS_POR_HORA = 3600
MICROSEGUNDOS_POR_MILISEGUNDO = 1000
UTC_OFFSET_SUFFIX = "+00:00"
ZULU_SUFFIX = "Z"
HORAS_POR_DIA = 24
DIAS_HASTA_CAMBIAR_UNIDAD = 2
ULTIMOS_DIGITOS_VISIBLES = 4
LONGITUD_MINIMA_PARA_ABREVIAR = 2
CARACTERES_POR_BLOQUE_BASE64 = 4
PARTES_CURSOR_LISTADO = 2
PARTES_CURSOR_POR_VENCER = 4

ACTOR_PREFIJO_USUARIO = "usuario:"
ACTOR_PREFIJO_SISTEMA = "sistema:"
NOMBRE_ACTOR_SISTEMA = "Sistema"
ACTOR_DESCONOCIDO = "una persona"
RECLAMANTE_ANONIMO = "Anónimo"
RECLAMANTE_SIN_DATOS = "Sin datos"
DNI_ENMASCARADO = "••••"
SIN_CATEGORIA = "sin-categoria"
MARCA_POR_VENCER = "por-vencer"
MARCA_VENCE_EN = "vence-en"
ZONA_DE_LIMA = "America/Lima"
PREFIJO_CODIGO_INCIDENCIA = "MINSA"
ANIO_DEL_CODIGO_DIGITOS = 4
SECUENCIA_DEL_CODIGO_DIGITOS_MINIMOS = 6
PARTES_DEL_CODIGO = 3
TIPOS_DE_IMAGEN_DE_EVIDENCIA = ("image/jpeg", "image/png", "image/webp")
INICIO_DE_DATA_URI = "data:"
SUFIJO_DE_DATA_URI_BASE64 = ";base64,"
CABECERAS_DE_IMAGEN = {
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "private, no-store",
    "Content-Disposition": "inline",
    "Content-Security-Policy": "default-src 'none'; sandbox",
}
DIGITOS_DEL_ANIO = 4
DIGITOS_DEL_MES_Y_DIA = 2
PARTES_DEL_DIA = 3
PALABRAS_QUE_SE_USAN = 2
