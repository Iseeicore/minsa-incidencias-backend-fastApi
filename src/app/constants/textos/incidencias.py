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
