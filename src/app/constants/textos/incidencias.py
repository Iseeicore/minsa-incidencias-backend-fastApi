from app.enums.accion_incidencia import AccionIncidencia

MENSAJE_CASO_NO_ENCONTRADO = "El caso solicitado no existe."
MENSAJE_EVIDENCIA_NO_ENCONTRADA = "La evidencia solicitada no existe."
MENSAJE_FECHA_INVALIDA = "La fecha debe ser un día real con el formato AAAA-MM-DD."
MENSAJE_ESTABLECIMIENTO_INVALIDO = "El código del establecimiento no es válido."
MENSAJE_RANGO_INVERTIDO = "La fecha «desde» no puede ser posterior a «hasta»."
MENSAJE_PLAZO_SOLO_CASOS_ABIERTOS = (
    "El plazo solo se aplica a los casos abiertos: no se combina con los estados «resuelto» y «archivado» "
    "ni con «motivoArchivo»."
)


def mensaje_rango_demasiado_largo(dias: int) -> str:
    return f"El rango no puede abarcar más de {dias} días."


TITULO_RESUELTO = "Caso resuelto"
TITULO_REABIERTO = "Caso reabierto"
TITULO_ARCHIVADO = "Archivado"
TITULO_CLASIFICACION_INICIAL = "Clasificación inicial registrada"
TITULO_DERIVADO = "Derivado al área"
TITULO_TOMADO = "Tomado en gestión"
TITULO_CATEGORIA_CORREGIDA = "Categoría corregida"
TITULO_CATEGORIA_CONFIRMADA = "Categoría confirmada"
TITULO_RECIBIDO_POR = "Recibido por"
DETALLE_REGISTRADO = "Registrado como incidencia."
SIN_CATEGORIA_ETIQUETA = "sin categoría"
CLASIFICADO_ETIQUETA = "Clasificado"


def detalle_por_actor(actor: str) -> str:
    return f"Por {actor}."


def detalle_hacia(destino: str, actor: str) -> str:
    return f"Hacia {destino}, por {actor}."


def detalle_de_uno_a_otro(antes: str, despues: str, actor: str) -> str:
    return f"De {antes} a {despues}, por {actor}."


def detalle_con_motivo(detalle: str, motivo: str) -> str:
    return f"{detalle} Motivo: {motivo}"


def texto_hace_menos_de_una_hora() -> str:
    return "hace menos de 1 h"


def texto_hace_horas(horas: int) -> str:
    return f"hace {horas} h"


def texto_hace_dias(dias: int) -> str:
    return f"hace {dias} d"


MENSAJE_ACCION_REALIZADA = {
    AccionIncidencia.CONFIRMAR: "Categoría confirmada.",
    AccionIncidencia.CORREGIR: "Categoría corregida.",
    AccionIncidencia.DERIVAR: "Caso derivado al área.",
    AccionIncidencia.TOMAR: "Caso tomado en gestión.",
    AccionIncidencia.RESOLVER: "Caso resuelto.",
    AccionIncidencia.ARCHIVAR: "Caso archivado.",
    AccionIncidencia.REABRIR: "Caso reabierto. Quedó en gestión.",
}
MENSAJE_ACCION_NO_PERMITIDA = {
    AccionIncidencia.CONFIRMAR: "No puedes confirmar la categoría de este caso.",
    AccionIncidencia.CORREGIR: "No puedes corregir la categoría de este caso.",
    AccionIncidencia.DERIVAR: "No puedes derivar este caso.",
    AccionIncidencia.TOMAR: "No puedes tomar este caso en gestión.",
    AccionIncidencia.RESOLVER: "No puedes resolver este caso.",
    AccionIncidencia.ARCHIVAR: "No puedes archivar este caso.",
    AccionIncidencia.REABRIR: "No puedes reabrir este caso.",
}
MENSAJE_MISMA_CATEGORIA = "La nueva categoría es igual a la actual."
MENSAJE_CATEGORIA_NO_PERMITIDA = "No puedes cambiar el caso a esa categoría."
MENSAJE_SIN_DESTINO_DE_DERIVACION = "El caso no tiene un destino vinculado válido para derivarlo."
MENSAJE_AREA_DESTINO_INVALIDA = "El área de destino no existe, está desactivada o no recibe este tipo de caso."
MENSAJE_DESTINO_NO_VINCULADO = (
    "Solo se puede derivar al establecimiento vinculado al caso; las denuncias por corrupción permanecen en OTRANS."
)
MENSAJE_DESCRIPCION_DERIVACION_INVALIDA = "Describe el motivo de la derivación con entre 10 y 2000 caracteres."
MENSAJE_VALOR_NULO = "El valor no puede ser nulo."


def mensaje_categoria_corregida_fuera_de_vista(etiqueta: str) -> str:
    return f"Categoría corregida a {etiqueta}. El caso pasó al área correspondiente y ya no aparece en tu lista."
