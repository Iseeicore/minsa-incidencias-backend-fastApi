from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants.clasificacion import INFORMACION_FALTANTE_POR_FALTANTE, VERSION_CLASIFICADOR_ALGORITMICO
from app.constants.incidencias import CATEGORIA_ETIQUETA
from app.constants.textos.clasificacion import (
    EXPLICACION_DE_APOYO,
    EXPLICACION_REVISION_OPCIONAL,
    EXPLICACION_REVISION_REQUERIDA,
    PLANTILLA_DE_EXPLICACION,
)
from app.filtro_corrupcion.domain.combinar_con_ia import combinar_reglas_con_ia
from app.filtro_corrupcion.domain.trazabilidad_normas import construir_trazabilidad_normas

if TYPE_CHECKING:
    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.informacion_faltante_ia import InformacionFaltanteIa
    from app.enums.origen_clasificacion import OrigenClasificacion
    from app.filtro_corrupcion.domain.tipos import (
        ReferenciaDerivacion,
        ResultadoCombinacion,
        ResultadoCorrupcion,
        SenalQuejaReclamo,
    )
    from app.filtro_corrupcion.domain.tipos_de_clasificacion import ResultadoClasificacion, ResumenCoincidencias
    from app.filtro_corrupcion.domain.trazabilidad_normas import TrazabilidadDeNormas


@dataclass(frozen=True, slots=True)
class DetalleDeClasificacion:
    version: str
    origen: OrigenClasificacion
    coincidencias: ResumenCoincidencias
    senales_queja_reclamo: tuple[SenalQuejaReclamo, ...]


@dataclass(frozen=True, slots=True)
class AnalisisClasificado:
    propuesta: CategoriaIncidencia
    confianza: float
    explicacion: str
    informacion_faltante: tuple[InformacionFaltanteIa, ...]
    ficha_derivacion: ReferenciaDerivacion | None
    requiere_otrans: bool
    revision_otrans: bool
    requiere_revision_humana: bool
    escalar_a_otrans: bool
    trazabilidad_normas: TrazabilidadDeNormas
    reglas: ResultadoCorrupcion
    combinacion: ResultadoCombinacion
    clasificacion: DetalleDeClasificacion


def adaptar_clasificacion(resultado: ResultadoClasificacion) -> AnalisisClasificado:
    reglas = resultado.reglas
    combinacion = combinar_reglas_con_ia(reglas, None)
    revision = EXPLICACION_REVISION_REQUERIDA if resultado.requiere_revision_humana else EXPLICACION_REVISION_OPCIONAL
    explicacion = PLANTILLA_DE_EXPLICACION.format(
        categoria=CATEGORIA_ETIQUETA[resultado.categoria],
        puntaje=reglas.puntaje,
        apoyo=EXPLICACION_DE_APOYO[resultado.coincidencias.estado],
        revision=revision,
    )
    return AnalisisClasificado(
        propuesta=resultado.categoria,
        confianza=combinacion.confianza,
        explicacion=explicacion,
        informacion_faltante=tuple(INFORMACION_FALTANTE_POR_FALTANTE[faltante] for faltante in reglas.faltantes),
        ficha_derivacion=reglas.referencia_derivacion,
        requiere_otrans=reglas.propuesta_corrupcion,
        revision_otrans=resultado.revision_otrans,
        requiere_revision_humana=resultado.requiere_revision_humana,
        escalar_a_otrans=reglas.escalar_a_otrans,
        trazabilidad_normas=construir_trazabilidad_normas(
            reglas, resultado.categoria, propuesta_corrupcion=reglas.propuesta_corrupcion
        ),
        reglas=reglas,
        combinacion=combinacion,
        clasificacion=DetalleDeClasificacion(
            version=VERSION_CLASIFICADOR_ALGORITMICO,
            origen=resultado.origen,
            coincidencias=resultado.coincidencias,
            senales_queja_reclamo=resultado.senales_queja_reclamo,
        ),
    )
