from typing import NamedTuple

from app.constants.textos.errores import DEFAULT_ERROR_MESSAGES
from app.enums.error_code import ErrorCode

CHECK_VIOLATION_SQLSTATE = "23514"
UNIQUE_VIOLATION_SQLSTATE = "23505"
MENSAJE_REGLA_DESCONOCIDA = "El cambio no cumple una regla del caso."
MENSAJE_DESCRIPCION_DERIVACION_SIN_BORDES = (
    "Describe el motivo de la derivación con entre 10 y 2000 caracteres, sin espacios al inicio o al final."
)


class ReglaDeLaBase(NamedTuple):
    fragmento: str
    mensaje: str
    corregible: bool = False
    codigo: ErrorCode | None = None


REGLAS_DE_LA_BASE: tuple[ReglaDeLaBase, ...] = (
    ReglaDeLaBase(
        "ck_incidencia_paciente_derivacion_descripcion", MENSAJE_DESCRIPCION_DERIVACION_SIN_BORDES, corregible=True
    ),
    ReglaDeLaBase("la categoria ya se corrigio una vez", "La categoría ya se corrigió una vez."),
    ReglaDeLaBase("ya se confirmo y no se puede corregir", "La categoría ya se confirmó y no se puede corregir."),
    ReglaDeLaBase("la confirmacion se registra una sola vez", "La categoría ya se confirmó."),
    ReglaDeLaBase(
        "una categoria corregida no se puede confirmar", "La categoría ya se corrigió y no se puede confirmar."
    ),
    ReglaDeLaBase(
        "no hay categoria de la IA que confirmar", "El caso todavía no tiene una categoría de la IA que confirmar."
    ),
    ReglaDeLaBase("la resolucion solo se registra una vez", "El caso ya tiene una resolución."),
    ReglaDeLaBase("transicion de estado no permitida", "El caso no puede pasar a ese estado desde el que tiene ahora."),
    ReglaDeLaBase(
        "exigen un area de destino", "El caso necesita un área de destino para derivarlo o tomarlo.", corregible=True
    ),
    ReglaDeLaBase(
        "solo se reasigna mientras el caso esta CLASIFICADO o DERIVADO",
        "El área de destino solo se cambia mientras el caso está clasificado o derivado.",
    ),
    ReglaDeLaBase("el area de destino esta desactivada", "El área de destino está desactivada.", corregible=True),
    ReglaDeLaBase(
        "un caso sensible solo se deriva a un area que reciba casos sensibles",
        "Una denuncia por corrupción solo se deriva a la oficina de transparencia (OTRANS), no a un establecimiento.",
        corregible=True,
    ),
    ReglaDeLaBase(
        "esta en un area que no recibe casos sensibles",
        "Una denuncia por corrupción no puede quedar en el área de un establecimiento.",
    ),
    ReglaDeLaBase(
        "el establecimiento de origen no se puede modificar",
        "El establecimiento de origen del caso no se puede cambiar.",
    ),
    ReglaDeLaBase(
        "el establecimiento de origen no existe o esta desactivado",
        "El establecimiento de origen no existe o está desactivado.",
        corregible=True,
    ),
    ReglaDeLaBase(
        "la resolucion exige las medidas tomadas y el fundamento",
        "Para resolver el caso hay que indicar las medidas tomadas y el fundamento "
        "(10 caracteres o más cada uno) y el resultado.",
        corregible=True,
    ),
    ReglaDeLaBase("archivar un caso exige un motivo de archivo", "Para archivar el caso hay que indicar el motivo."),
    ReglaDeLaBase(
        "el motivo de archivo solo se indica al archivar", "El motivo de archivo solo se indica al archivar el caso."
    ),
    ReglaDeLaBase(
        "un archivado manual exige una justificacion",
        "Para archivar el caso hay que explicar el motivo con 10 caracteres o más.",
        corregible=True,
    ),
    ReglaDeLaBase(
        "un archivado manual solo se hace desde un caso abierto",
        "Solo se archiva a mano un caso abierto: registrado, clasificado, derivado o en gestión.",
    ),
    ReglaDeLaBase(
        "un archivado manual (datos insuficientes o no corresponde) lo hace una persona",
        "Solo una persona archiva un caso a mano.",
    ),
    ReglaDeLaBase(
        "un caso abierto solo se archiva por vencimiento",
        "Un caso abierto solo se archiva cuando vence su plazo de atención.",
    ),
    ReglaDeLaBase("el motivo de archivo no corresponde", "El motivo de archivo no corresponde al estado del caso."),
    ReglaDeLaBase(
        "la justificacion del archivo solo se indica al archivar",
        "La justificación solo se indica al archivar el caso.",
    ),
    ReglaDeLaBase(
        "solo se reabre un caso archivado por datos insuficientes",
        "Este caso no se puede reabrir: solo se reabren los archivados por datos insuficientes, "
        "por no corresponder o por vencimiento sin atender.",
    ),
    ReglaDeLaBase(
        "reabrir un caso exige un motivo",
        "Para reabrir el caso hay que explicar el motivo con 10 caracteres o más.",
        corregible=True,
    ),
    ReglaDeLaBase(
        "el motivo de la reapertura solo se indica al reabrir",
        "El motivo de la reapertura solo se indica al reabrir el caso.",
    ),
    ReglaDeLaBase(
        "las fechas y actores de derivacion, toma, archivado y reapertura",
        "Las fechas y los responsables de la derivación, la toma, el archivo y la reapertura los llena el sistema.",
    ),
    ReglaDeLaBase(
        "el tipo de area del rol no coincide con el area del usuario",
        "El rol no corresponde al tipo de área del usuario.",
        corregible=True,
    ),
    ReglaDeLaBase(
        "el tipo de area no coincide con el de los roles del usuario",
        "El área no corresponde a los roles del usuario.",
        corregible=True,
    ),
    ReglaDeLaBase(
        "el rol esta desactivado y no se puede asignar",
        "El rol está desactivado y no se puede asignar.",
        corregible=True,
    ),
    ReglaDeLaBase(
        "el establecimiento ya tiene 3 usuarios activos",
        DEFAULT_ERROR_MESSAGES[ErrorCode.LIMITE_USUARIOS_ESTABLECIMIENTO],
        codigo=ErrorCode.LIMITE_USUARIOS_ESTABLECIMIENTO,
    ),
)
