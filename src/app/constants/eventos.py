EVENTOS_RUTA = "/eventos"
EVENTOS_AGRUPADO_SEGUNDOS = 1
EVENTOS_LATIDO_SEGUNDOS = 25
EVENTOS_REINTENTO_SEGUNDOS = 5
EVENTOS_REINTENTO_MS = 5000
EVENTOS_CATEGORIAS_CACHE_SEGUNDOS = 300
EVENTOS_MAX_POR_USUARIO = 3
EVENTOS_MAX_TOTAL = 500
EVENTOS_TIPO_DE_DISPARADOR = 29
EVENTOS_ID_MAXIMO_DE_ALCANCE = 9_007_199_254_740_991
EVENTOS_CARACTERES_VISIBLES = 4
EVENTOS_CABECERAS = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
}
EVENTOS_DATOS_VACIOS = "{}"
EVENTOS_COMENTARIO_DE_LATIDO = "latido"
EVENTOS_APLICACION = "minsa-incidencias-tiempo-real"
CANAL_CAMBIOS_INCIDENCIAS = "minsa_incidencias_cambio"
FUNCION_DE_NOTIFICACION = "chatbot.fn_notificar_cambio_incidencia"
DISPARADOR_DE_NOTIFICACION = "trg_incidencia_paciente_notificar_cambio"
CLAVE_DE_BLOQUEO_DE_INSTALACION = "minsa-incidencias:instalar-notificaciones"
VERSION_DE_NOTIFICACION = "minsa-incidencias:eventos-v2"
