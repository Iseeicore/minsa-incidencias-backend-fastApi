from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.estado_incidencia import EstadoIncidencia
    from app.enums.motivo_archivo import MotivoArchivo
    from app.enums.resultado_resolucion import ResultadoResolucion


@dataclass(frozen=True, slots=True)
class CasoConsultado:
    id: str
    codigo: str
    estado: EstadoIncidencia
    categoria: CategoriaIncidencia | None
    categoria_ia: CategoriaIncidencia | None
    confianza_ia: float | None
    fecha_creacion: datetime
    resuelto_en: datetime | None
    ahora: datetime
    revisada: bool
    corregida: bool
    area_codigo: str | None
    area_nombre: str | None
    area_destino_id: int | None
    area_origen_id: int | None
    establecimiento_codigo: str | None
    establecimiento_nombre: str | None
    establecimiento_nivel: str | None
    establecimiento_categoria: str | None
    responsable: str | None
    medidas_tomadas: str | None
    fundamento: str | None
    resultado_resolucion: ResultadoResolucion | None
    motivo_archivo: MotivoArchivo | None
    archivo_detalle: str | None
    archivado_en: datetime | None
    reabierto_en: datetime | None
    reabierto_motivo: str | None
    vence_atencion_en: datetime | None
    descripcion_derivacion: str | None
    descripcion: str
    es_anonimo: bool
    dni: str | None
    nombre: str | None
    canal: str
    sensible: bool


@dataclass(frozen=True, slots=True)
class EvidenciaConsultada:
    id: str
    nombre: str | None
    tipo: str
    tipo_nombre: str
    fecha: datetime
    verificada: bool
    contenido_disponible: bool


@dataclass(frozen=True, slots=True)
class ConteoPorVencer:
    total: int
    vencidos: int
