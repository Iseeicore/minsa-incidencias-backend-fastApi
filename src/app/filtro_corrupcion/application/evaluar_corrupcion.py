from dataclasses import dataclass

from app.filtro_corrupcion.domain.combinar_con_ia import combinar_reglas_con_ia
from app.filtro_corrupcion.domain.evaluar_texto import evaluar_texto_corrupcion
from app.filtro_corrupcion.domain.tipos import ContextoEvaluacion, EvaluacionDeCorrupcion


@dataclass(frozen=True, slots=True)
class SolicitudDeEvaluacion:
    texto: str
    contexto: ContextoEvaluacion
    combinar_con_ia: bool = False
    peso_ia: float | None = None


class EvaluarCorrupcion:
    def execute(self, solicitud: SolicitudDeEvaluacion) -> EvaluacionDeCorrupcion:
        resultado = evaluar_texto_corrupcion(solicitud.texto, solicitud.contexto)
        combinacion = combinar_reglas_con_ia(resultado, solicitud.peso_ia) if solicitud.combinar_con_ia else None
        return EvaluacionDeCorrupcion(resultado, combinacion)
