from app.constants.incidencias import (
    DNI_ENMASCARADO,
    LONGITUD_MINIMA_PARA_ABREVIAR,
    PALABRAS_QUE_SE_USAN,
    RECLAMANTE_ANONIMO,
    RECLAMANTE_SIN_DATOS,
    ULTIMOS_DIGITOS_VISIBLES,
)

SEPARADOR_DE_PARTES = " · "


def _abreviar_nombre(nombre: str) -> str:
    palabras = nombre.split()
    if not palabras:
        return ""
    if len(palabras) < PALABRAS_QUE_SE_USAN:
        return palabras[0]
    primera, segunda = palabras[0], palabras[1]
    if len(segunda) < LONGITUD_MINIMA_PARA_ABREVIAR:
        return f"{primera} {segunda}"
    return f"{primera} {segunda[0].upper()}."


def _enmascarar_dni(dni: str) -> str:
    limpio = dni.strip()
    if len(limpio) <= ULTIMOS_DIGITOS_VISIBLES:
        return DNI_ENMASCARADO
    return f"{DNI_ENMASCARADO}{limpio[-ULTIMOS_DIGITOS_VISIBLES:]}"


def describir_reclamante(*, es_anonimo: bool, nombre: str | None, dni: str | None) -> str:
    if es_anonimo:
        return RECLAMANTE_ANONIMO
    nombre_corto = _abreviar_nombre(nombre) if nombre else ""
    documento = f"DNI {_enmascarar_dni(dni)}" if dni and dni.strip() else ""
    partes = [parte for parte in (nombre_corto, documento) if parte]
    return SEPARADOR_DE_PARTES.join(partes) if partes else RECLAMANTE_SIN_DATOS
