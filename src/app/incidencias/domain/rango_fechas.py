from datetime import date

from app.constants.incidencias import DIGITOS_DEL_ANIO, DIGITOS_DEL_MES_Y_DIA, PARTES_DEL_DIA


def dia_de(texto: str) -> date | None:
    partes = texto.split("-")
    if len(partes) != PARTES_DEL_DIA:
        return None
    anio, mes, dia = partes
    forma_valida = (
        len(anio) == DIGITOS_DEL_ANIO
        and len(mes) == DIGITOS_DEL_MES_Y_DIA
        and len(dia) == DIGITOS_DEL_MES_Y_DIA
        and all(parte.isascii() and parte.isdigit() for parte in partes)
    )
    if not forma_valida:
        return None
    try:
        return date(int(anio), int(mes), int(dia))
    except ValueError:
        return None


def dias_del_rango(desde: str, hasta: str) -> int | None:
    inicio = dia_de(desde)
    fin = dia_de(hasta)
    if inicio is None or fin is None:
        return None
    return (fin - inicio).days + 1
