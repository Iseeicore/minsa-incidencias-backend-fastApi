from typing import TYPE_CHECKING

from app.constants.analisis import REQUISITO_POR_INFORMACION_FALTANTE
from app.constants.incidencias import CATEGORIA_API
from app.constants.normas import ETIQUETA_REFERENCIA_ORIENTATIVA
from app.enums.grupo_cita import GrupoCita
from app.incidencias.application.leer_senales_guardadas import leer_senales_guardadas
from app.incidencias.domain.analisis import (
    AnalisisDeIncidencia,
    AreaMencionada,
    CitaDeNorma,
    ModeloDelAnalisis,
    RequisitoFaltante,
)
from app.incidencias.domain.tiempo import a_iso
from app.shared.normas import fragmentos_por_id

if TYPE_CHECKING:
    from collections.abc import Mapping

    from app.incidencias.application.leer_senales_guardadas import SenalesGuardadas
    from app.incidencias.domain.analisis import CitaGuardada, FilaAnalisis
    from app.shared.normas import FragmentoNorma


def _cita_de_norma(cita: CitaGuardada, fragmentos: Mapping[str, FragmentoNorma]) -> CitaDeNorma:
    fragmento = fragmentos.get(cita.fragmento_id)
    return CitaDeNorma(
        fragmento_id=cita.fragmento_id,
        grupo=cita.grupo,
        referencia=fragmento.referencia if fragmento is not None else cita.referencia,
        titulo=fragmento.titulo if fragmento is not None else cita.referencia,
        texto=fragmento.texto if fragmento is not None else None,
        senales_que_la_motivan=cita.senales_que_la_motivan,
    )


def _requisitos(guardado: SenalesGuardadas, fragmentos: Mapping[str, FragmentoNorma]) -> tuple[RequisitoFaltante, ...]:
    requisitos: list[RequisitoFaltante] = []
    for faltante in guardado.informacion_faltante:
        fragmento = fragmentos.get(REQUISITO_POR_INFORMACION_FALTANTE[faltante])
        if fragmento is not None:
            requisitos.append(RequisitoFaltante(faltante.value, fragmento.referencia, fragmento.texto))
    return tuple(requisitos)


def armar_analisis(
    codigo: str, fila: FilaAnalisis, fragmentos: Mapping[str, FragmentoNorma] | None = None
) -> AnalisisDeIncidencia:
    por_id = fragmentos if fragmentos is not None else fragmentos_por_id()
    guardado = leer_senales_guardadas(fila.senales)
    normas = guardado.normas
    decision = guardado.decision
    modelo = guardado.modelo
    citas = tuple(_cita_de_norma(cita, por_id) for cita in (normas.citas if normas is not None else ()))
    propuesta = decision.propuesta_del_analisis if decision is not None else None
    area = (
        AreaMencionada(fila.area_mencionada_codigo, fila.area_mencionada_nombre)
        if fila.area_mencionada_codigo and fila.area_mencionada_nombre
        else None
    )
    return AnalisisDeIncidencia(
        codigo=codigo,
        categoria_ia=CATEGORIA_API[fila.categoria_ia] if fila.categoria_ia is not None else None,
        confianza_ia=fila.confianza_ia,
        version_clasificador=fila.version_clasificador,
        version_reglas=fila.version_reglas,
        puntaje=fila.puntaje,
        motivo_de_escritura=decision.motivo if decision is not None else None,
        propuesta_del_analisis=CATEGORIA_API[propuesta] if propuesta is not None else None,
        requiere_revision_humana=decision.requiere_revision_humana if decision is not None else False,
        escalar_a_otrans=decision.escalar_a_otrans if decision is not None else False,
        explicacion=guardado.explicacion,
        senales=guardado.senales,
        supuestos=tuple(cita for cita in citas if cita.grupo == GrupoCita.SUPUESTO),
        procedimiento=tuple(cita for cita in citas if cita.grupo == GrupoCita.PROCEDIMIENTO),
        sin_supuesto_identificado=normas.sin_supuesto_identificado if normas is not None else False,
        etiqueta_normas=ETIQUETA_REFERENCIA_ORIENTATIVA,
        version_normas=normas.version if normas is not None else None,
        transcripcion_anexo_c_cotejada=normas.transcripcion_anexo_c_cotejada if normas is not None else False,
        requisitos_faltantes=_requisitos(guardado, por_id),
        ficha_derivacion=guardado.ficha_derivacion,
        cargo_mencionado=fila.cargo_mencionado,
        nombre_mencionado=fila.nombre_mencionado,
        area_mencionada=area,
        modelo=ModeloDelAnalisis(
            variante=modelo.variante if modelo is not None else None,
            degradado=modelo.degradado if modelo is not None else False,
            peso_ia=decision.peso_ia if decision is not None else None,
        ),
        fecha_analisis=a_iso(fila.fecha_analisis),
    )
