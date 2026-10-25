from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants.clasificacion import VERSION_CLASIFICADOR_ALGORITMICO
from app.filtro_corrupcion.domain.adaptar_clasificacion import adaptar_clasificacion
from app.filtro_corrupcion.domain.clasificar_por_coincidencias import aplicar_coincidencias, clasificar_por_reglas
from app.filtro_corrupcion.domain.regla_de_escritura import construir_version_clasificador, decidir_escritura
from app.filtro_corrupcion.domain.senales_guardadas import construir_senales_guardadas

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from app.filtro_corrupcion.domain.regla_de_escritura import DecisionDeEscritura
    from app.filtro_corrupcion.domain.senales_guardadas import SenalesGuardadas
    from app.filtro_corrupcion.domain.tipos import ContextoEvaluacion, ResultadoCorrupcion
    from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia

type BuscadorCoincidencias = Callable[[str], Awaitable[Iterable[CandidatoCoincidencia]]]


@dataclass(frozen=True, slots=True)
class CasoAnalizado:
    decision: DecisionDeEscritura
    version: str
    reglas: ResultadoCorrupcion
    senales: SenalesGuardadas


async def analizar_caso(
    texto: str, contexto: ContextoEvaluacion, buscar_coincidencias: BuscadorCoincidencias | None
) -> CasoAnalizado:
    resultado = clasificar_por_reglas(texto, contexto)
    if buscar_coincidencias is not None and not resultado.revision_otrans:
        resultado = aplicar_coincidencias(resultado, await buscar_coincidencias(texto))
    analisis = adaptar_clasificacion(resultado)
    decision = decidir_escritura(analisis)
    return CasoAnalizado(
        decision=decision,
        version=construir_version_clasificador(analisis.reglas.version_reglas, VERSION_CLASIFICADOR_ALGORITMICO),
        reglas=analisis.reglas,
        senales=construir_senales_guardadas(analisis, decision),
    )
