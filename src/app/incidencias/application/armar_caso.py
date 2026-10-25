from typing import TYPE_CHECKING

from app.constants.incidencias import CATEGORIA_API, ESTADO_API
from app.incidencias.domain.casos import (
    ArchivoDeCaso,
    AreaDeCaso,
    CasoDetalle,
    CasoResumen,
    EstablecimientoDeCaso,
    EvidenciaDeCaso,
    ReaperturaDeCaso,
    ResolucionDeCaso,
)
from app.incidencias.domain.historial import construir_historial
from app.incidencias.domain.plazo import calcular_plazo
from app.incidencias.domain.reclamante import describir_reclamante
from app.incidencias.domain.tiempo import a_iso, horas_entre
from app.shared.acciones_permitidas import CasoParaAcciones, acciones_permitidas

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.incidencias.domain.caso_consultado import CasoConsultado, EvidenciaConsultada
    from app.incidencias.domain.fila_historial import FilaHistorial
    from app.incidencias.domain.plazo import PlazosConfigurados
    from app.shared.sesion import SesionActual


def resumir(fila: CasoConsultado, sesion: SesionActual | None, plazos: PlazosConfigurados) -> CasoResumen:
    area = AreaDeCaso(fila.area_codigo, fila.area_nombre) if fila.area_codigo and fila.area_nombre else None
    establecimiento = (
        EstablecimientoDeCaso(
            fila.establecimiento_codigo,
            fila.establecimiento_nombre,
            fila.establecimiento_nivel,
            fila.establecimiento_categoria,
        )
        if fila.establecimiento_codigo and fila.establecimiento_nombre
        else None
    )
    acciones = (
        tuple(acciones_permitidas(sesion.roles, CasoParaAcciones(fila.estado, fila.categoria, fila.revisada)))
        if sesion is not None
        else ()
    )
    return CasoResumen(
        codigo=fila.codigo,
        categoria=CATEGORIA_API[fila.categoria] if fila.categoria is not None else None,
        categoria_ia=CATEGORIA_API[fila.categoria_ia] if fila.categoria_ia is not None else None,
        confianza_ia=fila.confianza_ia,
        area=area,
        establecimiento=establecimiento,
        responsable=fila.responsable,
        estado=ESTADO_API[fila.estado],
        horas_desde_llegada=max(0, horas_entre(fila.fecha_creacion, fila.ahora)),
        horas_desde_resolucion=max(0, horas_entre(fila.resuelto_en, fila.ahora)) if fila.resuelto_en else None,
        revisado_por_humano=fila.revisada,
        corregida=fila.corregida,
        plazo=calcular_plazo(fila.estado, fila.vence_atencion_en, fila.resuelto_en, fila.ahora, plazos),
        acciones=acciones,
    )


def _evidencias(fila: CasoConsultado, evidencias: Sequence[EvidenciaConsultada]) -> tuple[EvidenciaDeCaso, ...]:
    return tuple(
        EvidenciaDeCaso(
            id=evidencia.id,
            nombre=evidencia.nombre or f"{evidencia.tipo_nombre} {indice + 1}",
            tipo=evidencia.tipo.lower(),
            fecha=a_iso(evidencia.fecha),
            sensible=fila.sensible,
            verificada=evidencia.verificada,
            contenido_disponible=evidencia.contenido_disponible,
        )
        for indice, evidencia in enumerate(evidencias)
    )


def detallar(
    fila: CasoConsultado,
    sesion: SesionActual | None,
    plazos: PlazosConfigurados,
    evidencias: Sequence[EvidenciaConsultada],
    historial: Sequence[FilaHistorial],
) -> CasoDetalle:
    resolucion = (
        ResolucionDeCaso(fila.medidas_tomadas, fila.fundamento, fila.resultado_resolucion)
        if fila.medidas_tomadas is not None and fila.fundamento is not None and fila.resultado_resolucion is not None
        else None
    )
    archivo = (
        ArchivoDeCaso(fila.motivo_archivo, fila.archivo_detalle, a_iso(fila.archivado_en))
        if fila.motivo_archivo is not None and fila.archivado_en is not None
        else None
    )
    reapertura = (
        ReaperturaDeCaso(a_iso(fila.reabierto_en), fila.reabierto_motivo)
        if fila.reabierto_en is not None and fila.reabierto_motivo is not None
        else None
    )
    return CasoDetalle(
        resumen=resumir(fila, sesion, plazos),
        descripcion_derivacion=fila.descripcion_derivacion,
        resolucion=resolucion,
        archivo=archivo,
        reapertura=reapertura,
        descripcion=fila.descripcion,
        reclamante=describir_reclamante(es_anonimo=fila.es_anonimo, nombre=fila.nombre, dni=fila.dni),
        evidencias=_evidencias(fila, evidencias),
        historial=tuple(construir_historial(historial, fila.canal, fila.ahora)),
    )
