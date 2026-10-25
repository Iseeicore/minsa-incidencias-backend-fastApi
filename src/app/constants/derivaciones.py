from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.situacion_derivacion import SituacionDerivacion

DERIVACIONES_LIMITE_POR_DEFECTO = 10
DERIVACIONES_LIMITE_MAXIMO = 100
DERIVACIONES_CURSOR_LONGITUD_MAXIMA = 200
MARCA_DE_DERIVACIONES = "derivaciones"
PARTES_CURSOR_DERIVACION = 3
IDENTIFICADOR_DE_DERIVACION_DIGITOS_MAXIMOS = 19
ESTADOS_DE_DERIVACION: dict[SituacionDerivacion, tuple[EstadoIncidencia, ...]] = {
    SituacionDerivacion.PENDIENTE: (
        EstadoIncidencia.REGISTRADO,
        EstadoIncidencia.CLASIFICADO,
        EstadoIncidencia.DERIVADO,
    ),
    SituacionDerivacion.EN_GESTION: (EstadoIncidencia.EN_GESTION,),
    SituacionDerivacion.RESUELTO: (EstadoIncidencia.RESUELTO,),
    SituacionDerivacion.ARCHIVADO: (EstadoIncidencia.ARCHIVADO,),
}
