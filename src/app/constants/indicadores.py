from app.enums.periodo_indicadores import PeriodoIndicadores
from app.enums.tarjeta_codigo import TarjetaCodigo

PERIODO_POR_DEFECTO = PeriodoIndicadores.SIETE_DIAS
DIAS_DEL_PERIODO: dict[PeriodoIndicadores, int] = {
    PeriodoIndicadores.SIETE_DIAS: 7,
    PeriodoIndicadores.TREINTA_DIAS: 30,
    PeriodoIndicadores.NOVENTA_DIAS: 90,
}
DIAS_POR_CUBO_DE_EVOLUCION: dict[PeriodoIndicadores, int] = {
    PeriodoIndicadores.SIETE_DIAS: 1,
    PeriodoIndicadores.TREINTA_DIAS: 1,
    PeriodoIndicadores.NOVENTA_DIAS: 7,
}
TARJETAS_EN_ORDEN = tuple(TarjetaCodigo)
TARJETAS_DEL_TABLERO = (
    TarjetaCodigo.RECIBIDOS,
    TarjetaCodigo.PENDIENTES,
    TarjetaCodigo.EN_GESTION,
    TarjetaCodigo.RESUELTOS,
)
DECIMALES_DEL_TIEMPO_PROMEDIO = 1
ESCALA_DEL_TIEMPO_PROMEDIO: float = 10**DECIMALES_DEL_TIEMPO_PROMEDIO
PERIODOS_INCLUIDOS_EN_COMPARACION = 2
FORMATO_DE_DIA_SQL = "YYYY-MM-DD"
