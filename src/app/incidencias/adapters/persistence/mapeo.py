from collections.abc import Mapping
from typing import Any

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.resultado_resolucion import ResultadoResolucion
from app.incidencias.domain.caso_consultado import CasoConsultado
from app.incidencias.domain.derivaciones import DerivacionConsultada
from app.incidencias.domain.fila_historial import FilaHistorial

type Fila = Mapping[Any, Any]


def _opcional[T](valor: object, construir: type[T]) -> T | None:
    return construir(valor) if valor is not None else None  # type: ignore[call-arg]


def caso_de(fila: Fila) -> CasoConsultado:
    return CasoConsultado(
        id=str(fila["id"]),
        codigo=fila["codigo"],
        estado=EstadoIncidencia(fila["estado"]),
        categoria=_opcional(fila["categoria"], CategoriaIncidencia),
        categoria_ia=_opcional(fila["categoria_ia"], CategoriaIncidencia),
        confianza_ia=fila["confianza_ia"],
        fecha_creacion=fila["fecha_creacion"],
        resuelto_en=fila["resuelto_en"],
        ahora=fila["ahora"],
        revisada=fila["revisada"],
        corregida=fila["corregida"],
        area_codigo=fila["area_codigo"],
        area_nombre=fila["area_nombre"],
        area_destino_id=fila["area_destino_id"],
        area_origen_id=fila["area_origen_id"],
        establecimiento_codigo=fila["establecimiento_codigo"],
        establecimiento_nombre=fila["establecimiento_nombre"],
        establecimiento_nivel=fila["establecimiento_nivel"],
        establecimiento_categoria=fila["establecimiento_categoria"],
        responsable=fila["responsable"],
        medidas_tomadas=fila["medidas_tomadas"],
        fundamento=fila["fundamento"],
        resultado_resolucion=_opcional(fila["resultado_resolucion"], ResultadoResolucion),
        motivo_archivo=_opcional(fila["motivo_archivo"], MotivoArchivo),
        archivo_detalle=fila["archivo_detalle"],
        archivado_en=fila["archivado_en"],
        reabierto_en=fila["reabierto_en"],
        reabierto_motivo=fila["reabierto_motivo"],
        vence_atencion_en=fila["vence_atencion_en"],
        descripcion_derivacion=fila["descripcion_derivacion"],
        descripcion=fila["descripcion"],
        es_anonimo=fila["es_anonimo"],
        dni=fila["dni"],
        nombre=fila["nombre"],
        canal=fila["canal"],
        sensible=fila["sensible"],
    )


def derivacion_de(fila: Fila) -> DerivacionConsultada:
    return DerivacionConsultada(
        id=fila["id"],
        codigo_caso=fila["codigo_caso"],
        fecha_derivacion=fila["fecha_derivacion"],
        origen_codigo=fila["origen_codigo"],
        origen_nombre=fila["origen_nombre"],
        destino_codigo=fila["destino_codigo"],
        destino_nombre=fila["destino_nombre"],
        destino_renipress=fila["destino_renipress"],
        derivado_por=fila["derivado_por"],
        descripcion=fila["descripcion"],
        categoria=_opcional(fila["categoria"], CategoriaIncidencia),
        estado=EstadoIncidencia(fila["estado"]),
        motivo_archivo=_opcional(fila["motivo_archivo"], MotivoArchivo),
    )


def fila_de_historial(fila: Fila) -> FilaHistorial:
    return FilaHistorial(
        operacion=fila["operacion"],
        actor=fila["actor"],
        actor_nombre=fila["actor_nombre"],
        fecha_hora=fila["fecha_hora"],
        ia=fila["ia"],
        categoria_ia=_opcional(fila["categoria_ia"], CategoriaIncidencia),
        confianza=fila["confianza"],
        version=fila["version"],
        corregida=fila["corregida"],
        categoria_antes=_opcional(fila["categoria_antes"], CategoriaIncidencia),
        categoria_despues=_opcional(fila["categoria_despues"], CategoriaIncidencia),
        confirmada=fila["confirmada"],
        estado_nuevo=_opcional(fila["estado_nuevo"], EstadoIncidencia),
        area_antes=fila["area_antes"],
        area_despues=fila["area_despues"],
        descripcion_derivacion=fila["descripcion_derivacion"],
        resolvio=fila["resolvio"],
        reabrio=fila["reabrio"],
    )
