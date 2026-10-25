import math
from dataclasses import replace
from typing import TYPE_CHECKING

from app.constants.clasificacion import (
    FACTOR_CUATRO_DECIMALES,
    MARGEN_MINIMO_COINCIDENCIA,
    SIMILITUD_MAXIMA_VALIDA,
    SIMILITUD_MINIMA_COINCIDENCIA,
    SIMILITUD_MINIMA_VALIDA,
)
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_coincidencias import EstadoCoincidencias
from app.enums.origen_clasificacion import OrigenClasificacion
from app.filtro_corrupcion.domain.combinar_con_ia import redondear_como_js
from app.filtro_corrupcion.domain.evaluar_texto import evaluar_texto_corrupcion
from app.filtro_corrupcion.domain.queja_reclamo import evaluar_texto_queja_reclamo
from app.filtro_corrupcion.domain.tipos import ContextoEvaluacion
from app.filtro_corrupcion.domain.tipos_de_clasificacion import (
    CandidatoCoincidencia,
    ResultadoClasificacion,
    ResumenCoincidencias,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.filtro_corrupcion.domain.tipos import SenalQuejaReclamo


def _mejores_por_categoria(candidatos: Iterable[CandidatoCoincidencia]) -> list[CandidatoCoincidencia]:
    mejores: dict[CategoriaIncidencia, float] = {}
    for candidato in candidatos:
        valida = math.isfinite(candidato.similitud) and (
            SIMILITUD_MINIMA_VALIDA <= candidato.similitud <= SIMILITUD_MAXIMA_VALIDA
        )
        if valida and candidato.similitud > mejores.get(candidato.categoria, -1):
            mejores[candidato.categoria] = candidato.similitud
    ordenados = sorted(mejores.items(), key=lambda par: (-par[1], par[0]))
    return [CandidatoCoincidencia(categoria, similitud) for categoria, similitud in ordenados]


def _resumir_coincidencias(candidatos: Iterable[CandidatoCoincidencia]) -> ResumenCoincidencias:
    mejores = _mejores_por_categoria(candidatos)
    if not mejores:
        return ResumenCoincidencias(EstadoCoincidencias.SIN_CANDIDATOS, None, None)
    mejor = mejores[0]
    segunda = mejores[1].similitud if len(mejores) > 1 else 0
    margen = redondear_como_js((mejor.similitud - segunda) * FACTOR_CUATRO_DECIMALES) / FACTOR_CUATRO_DECIMALES
    suficiente = mejor.similitud >= SIMILITUD_MINIMA_COINCIDENCIA and margen >= MARGEN_MINIMO_COINCIDENCIA
    estado = EstadoCoincidencias.CORROBORADA if suficiente else EstadoCoincidencias.INSUFICIENTE
    return ResumenCoincidencias(estado, mejor, margen)


def _es_mixta(senales: Iterable[SenalQuejaReclamo]) -> bool:
    categorias = {senal.categoria for senal in senales}
    return CategoriaIncidencia.QUEJA in categorias and CategoriaIncidencia.RECLAMO in categorias


def _admite_apoyo(base: ResultadoClasificacion, categoria: CategoriaIncidencia) -> bool:
    if categoria in (CategoriaIncidencia.DENUNCIA_CORRUPCION, CategoriaIncidencia.OTRO):
        return False
    if base.reglas.senal_sensible is not None:
        return categoria == base.categoria
    tiene_senal = any(senal.categoria == categoria for senal in base.senales_queja_reclamo)
    return tiene_senal and (categoria == base.categoria or _es_mixta(base.senales_queja_reclamo))


def clasificar_por_reglas(texto: str, contexto: ContextoEvaluacion | None = None) -> ResultadoClasificacion:
    reglas = evaluar_texto_corrupcion(texto, contexto or ContextoEvaluacion())
    queja_reclamo = evaluar_texto_queja_reclamo(texto)
    revision_otrans = reglas.propuesta_corrupcion or reglas.requiere_segunda_opinion
    categoria = (
        CategoriaIncidencia.DENUNCIA_CORRUPCION
        if revision_otrans
        else (reglas.categoria_sugerida or queja_reclamo.categoria or CategoriaIncidencia.OTRO)
    )
    return ResultadoClasificacion(
        categoria=categoria,
        reglas=reglas,
        senales_queja_reclamo=queja_reclamo.senales,
        requiere_revision_humana=True,
        revision_otrans=revision_otrans,
        origen=OrigenClasificacion.SIN_COINCIDENCIAS
        if categoria == CategoriaIncidencia.OTRO
        else OrigenClasificacion.REGLAS,
        coincidencias=ResumenCoincidencias(EstadoCoincidencias.NO_CONSULTADA, None, None),
    )


def aplicar_coincidencias(
    base: ResultadoClasificacion, candidatos: Iterable[CandidatoCoincidencia]
) -> ResultadoClasificacion:
    coincidencias = _resumir_coincidencias(candidatos)
    if coincidencias.estado != EstadoCoincidencias.CORROBORADA or coincidencias.mejor is None:
        return replace(base, coincidencias=coincidencias)
    if not _admite_apoyo(base, coincidencias.mejor.categoria):
        return replace(base, coincidencias=replace(coincidencias, estado=EstadoCoincidencias.CONTRADICTORIA))
    return replace(
        base,
        categoria=coincidencias.mejor.categoria,
        origen=OrigenClasificacion.REGLAS_CON_APOYO_BD,
        requiere_revision_humana=_es_mixta(base.senales_queja_reclamo) or base.reglas.senal_sensible is not None,
        coincidencias=coincidencias,
    )
