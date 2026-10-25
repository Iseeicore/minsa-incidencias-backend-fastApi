from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants.clasificacion import TOPE_CONFIANZA_CON_DUDA
from app.constants.filtro_corrupcion import FACTOR_DOS_DECIMALES, TOPE_CONFIANZA
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.enums.origen_propuesta import OrigenPropuesta
from app.filtro_corrupcion.domain.combinar_con_ia import redondear_como_js

if TYPE_CHECKING:
    from app.filtro_corrupcion.domain.adaptar_clasificacion import AnalisisClasificado


@dataclass(frozen=True, slots=True)
class DecisionDeEscritura:
    categoria: CategoriaIncidencia
    confianza: float
    motivo: MotivoDeEscritura
    propuesta_del_analisis: CategoriaIncidencia
    escalar_a_otrans: bool


def _confianza_acotada(confianza: float, tope: float) -> float:
    acotada = min(max(confianza, 0), tope, TOPE_CONFIANZA)
    return redondear_como_js(acotada * FACTOR_DOS_DECIMALES) / FACTOR_DOS_DECIMALES


def _motivo_de_corrupcion(analisis: AnalisisClasificado) -> MotivoDeEscritura:
    if analisis.reglas.origen_propuesta == OrigenPropuesta.IDENTIDAD:
        return MotivoDeEscritura.IDENTIDAD
    return MotivoDeEscritura.REGLAS


def decidir_escritura(analisis: AnalisisClasificado) -> DecisionDeEscritura:
    if analisis.requiere_otrans:
        categoria = CategoriaIncidencia.DENUNCIA_CORRUPCION
        confianza = _confianza_acotada(analisis.confianza, TOPE_CONFIANZA)
        motivo = _motivo_de_corrupcion(analisis)
    elif analisis.revision_otrans:
        categoria = CategoriaIncidencia.DENUNCIA_CORRUPCION
        confianza = _confianza_acotada(analisis.confianza, TOPE_CONFIANZA_CON_DUDA)
        motivo = MotivoDeEscritura.DUDA_SIN_MODELO
    else:
        categoria = analisis.propuesta
        confianza = _confianza_acotada(analisis.confianza, TOPE_CONFIANZA)
        motivo = MotivoDeEscritura.SIN_CORRUPCION
    return DecisionDeEscritura(
        categoria=categoria,
        confianza=confianza,
        motivo=motivo,
        propuesta_del_analisis=analisis.propuesta,
        escalar_a_otrans=analisis.escalar_a_otrans,
    )


def construir_version_clasificador(version_reglas: str, version_motor: str) -> str:
    return f"{version_reglas}+{version_motor}"
