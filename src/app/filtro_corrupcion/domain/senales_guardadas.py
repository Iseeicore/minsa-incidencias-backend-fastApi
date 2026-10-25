from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.informacion_faltante_ia import InformacionFaltanteIa
    from app.enums.motivo_de_escritura import MotivoDeEscritura
    from app.filtro_corrupcion.domain.adaptar_clasificacion import AnalisisClasificado, DetalleDeClasificacion
    from app.filtro_corrupcion.domain.regla_de_escritura import DecisionDeEscritura
    from app.filtro_corrupcion.domain.tipos import ReferenciaDerivacion, SenalDetectada
    from app.filtro_corrupcion.domain.trazabilidad_normas import CitaDeNormaClasificada


@dataclass(frozen=True, slots=True)
class DecisionGuardada:
    categoria_escrita: CategoriaIncidencia
    motivo: MotivoDeEscritura
    propuesta_del_analisis: CategoriaIncidencia
    confianza_del_analisis: float
    confianza_escrita: float
    escalar_a_otrans: bool
    requiere_revision_humana: bool
    revision_otrans: bool
    puntaje_reglas: int
    puntaje_total: int


@dataclass(frozen=True, slots=True)
class NormasGuardadas:
    version: str
    etiqueta: str
    transcripcion_anexo_c_cotejada: bool
    sin_supuesto_identificado: bool
    citas: tuple[CitaDeNormaClasificada, ...]


@dataclass(frozen=True, slots=True)
class SenalesGuardadas:
    senales: tuple[SenalDetectada, ...]
    informacion_faltante: tuple[InformacionFaltanteIa, ...]
    ficha_derivacion: ReferenciaDerivacion | None
    normas: NormasGuardadas
    clasificacion: DetalleDeClasificacion
    explicacion: str
    decision: DecisionGuardada


def construir_senales_guardadas(analisis: AnalisisClasificado, decision: DecisionDeEscritura) -> SenalesGuardadas:
    trazabilidad = analisis.trazabilidad_normas
    return SenalesGuardadas(
        senales=analisis.reglas.senales,
        informacion_faltante=analisis.informacion_faltante,
        ficha_derivacion=analisis.ficha_derivacion,
        normas=NormasGuardadas(
            version=trazabilidad.version,
            etiqueta=trazabilidad.etiqueta,
            transcripcion_anexo_c_cotejada=trazabilidad.transcripcion_anexo_c_cotejada,
            sin_supuesto_identificado=trazabilidad.sin_supuesto_identificado,
            citas=(*trazabilidad.supuestos, *trazabilidad.procedimiento),
        ),
        clasificacion=analisis.clasificacion,
        explicacion=analisis.explicacion,
        decision=DecisionGuardada(
            categoria_escrita=decision.categoria,
            motivo=decision.motivo,
            propuesta_del_analisis=decision.propuesta_del_analisis,
            confianza_del_analisis=analisis.confianza,
            confianza_escrita=decision.confianza,
            escalar_a_otrans=decision.escalar_a_otrans,
            requiere_revision_humana=analisis.requiere_revision_humana,
            revision_otrans=analisis.revision_otrans,
            puntaje_reglas=analisis.combinacion.puntaje_reglas,
            puntaje_total=analisis.combinacion.puntaje_total,
        ),
    )
