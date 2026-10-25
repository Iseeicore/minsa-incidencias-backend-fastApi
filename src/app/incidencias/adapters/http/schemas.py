from typing import TYPE_CHECKING, Self

from pydantic import Field

from app.enums.accion_incidencia import AccionIncidencia
from app.enums.categoria_api import CategoriaApi
from app.enums.estado_api import EstadoApi
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.plazo_estado import PlazoEstado
from app.enums.plazo_tipo import PlazoTipo
from app.enums.resultado_resolucion import ResultadoResolucion
from app.shared.api_model import ApiModel
from app.shared.pagina_response import PaginaResponse

if TYPE_CHECKING:
    from app.incidencias.domain.casos import (
        CasoDetalle,
        CasoResumen,
        CasosPorVencer,
        ConteoAcotado,
        ConteosDeCasos,
    )
    from app.shared.pagination import Pagina


class AreaDeCasoResponse(ApiModel):
    codigo: str
    nombre: str


class EstablecimientoDeCasoResponse(ApiModel):
    codigo_renipress: str
    nombre: str
    nivel_atencion: str | None
    categoria: str | None


class PlazoResponse(ApiModel):
    tipo: PlazoTipo | None
    estado: PlazoEstado | None
    vence_en: str | None
    horas_restantes: int | None


class CasoResumenResponse(ApiModel):
    codigo: str
    categoria: CategoriaApi | None
    categoria_ia: CategoriaApi | None
    confianza_ia: float | None
    etiquetas: list[str]
    prioridad: None
    organismo: None
    area: AreaDeCasoResponse | None
    establecimiento: EstablecimientoDeCasoResponse | None
    responsable: str | None
    estado: EstadoApi
    horas_desde_llegada: int
    horas_desde_resolucion: int | None
    revisado_por_humano: bool
    corregida: bool
    plazo: PlazoResponse
    acciones: list[AccionIncidencia]

    @classmethod
    def desde_dominio(cls, caso: CasoResumen) -> Self:
        return cls(**_campos_de_resumen(caso))


class EvidenciaResponse(ApiModel):
    id: str
    nombre: str
    tipo: str
    fecha: str
    sensible: bool
    verificada: bool
    contenido_disponible: bool


class ResolucionResponse(ApiModel):
    medidas_tomadas: str
    fundamento: str
    resultado: ResultadoResolucion


class ArchivoResponse(ApiModel):
    motivo: MotivoArchivo
    detalle: str | None
    archivado_en: str


class ReaperturaResponse(ApiModel):
    reabierto_en: str
    motivo: str


class ItemDeHistorialResponse(ApiModel):
    titulo: str
    detalle: str
    hora: str
    fecha: str


class CasoDetalleResponse(CasoResumenResponse):
    descripcion_derivacion: str | None
    resolucion: ResolucionResponse | None
    archivo: ArchivoResponse | None
    reapertura: ReaperturaResponse | None
    descripcion: str
    reclamante: str
    evidencias: list[EvidenciaResponse]
    historial: list[ItemDeHistorialResponse]

    @classmethod
    def desde_dominio(cls, caso: CasoDetalle) -> Self:  # type: ignore[override]
        resolucion = caso.resolucion
        archivo = caso.archivo
        reapertura = caso.reapertura
        return cls(
            **_campos_de_resumen(caso.resumen),
            descripcion_derivacion=caso.descripcion_derivacion,
            resolucion=ResolucionResponse(
                medidas_tomadas=resolucion.medidas_tomadas,
                fundamento=resolucion.fundamento,
                resultado=resolucion.resultado,
            )
            if resolucion
            else None,
            archivo=ArchivoResponse(motivo=archivo.motivo, detalle=archivo.detalle, archivado_en=archivo.archivado_en)
            if archivo
            else None,
            reapertura=ReaperturaResponse(reabierto_en=reapertura.reabierto_en, motivo=reapertura.motivo)
            if reapertura
            else None,
            descripcion=caso.descripcion,
            reclamante=caso.reclamante,
            evidencias=[
                EvidenciaResponse(
                    id=evidencia.id,
                    nombre=evidencia.nombre,
                    tipo=evidencia.tipo,
                    fecha=evidencia.fecha,
                    sensible=evidencia.sensible,
                    verificada=evidencia.verificada,
                    contenido_disponible=evidencia.contenido_disponible,
                )
                for evidencia in caso.evidencias
            ],
            historial=[
                ItemDeHistorialResponse(titulo=item.titulo, detalle=item.detalle, hora=item.hora, fecha=item.fecha)
                for item in caso.historial
            ],
        )


def _campos_de_resumen(caso: CasoResumen) -> dict[str, object]:
    return {
        "codigo": caso.codigo,
        "categoria": caso.categoria,
        "categoria_ia": caso.categoria_ia,
        "confianza_ia": caso.confianza_ia,
        "etiquetas": [],
        "prioridad": None,
        "organismo": None,
        "area": AreaDeCasoResponse(codigo=caso.area.codigo, nombre=caso.area.nombre) if caso.area else None,
        "establecimiento": EstablecimientoDeCasoResponse(
            codigo_renipress=caso.establecimiento.codigo_renipress,
            nombre=caso.establecimiento.nombre,
            nivel_atencion=caso.establecimiento.nivel_atencion,
            categoria=caso.establecimiento.categoria,
        )
        if caso.establecimiento
        else None,
        "responsable": caso.responsable,
        "estado": caso.estado,
        "horas_desde_llegada": caso.horas_desde_llegada,
        "horas_desde_resolucion": caso.horas_desde_resolucion,
        "revisado_por_humano": caso.revisado_por_humano,
        "corregida": caso.corregida,
        "plazo": PlazoResponse(
            tipo=caso.plazo.tipo,
            estado=caso.plazo.estado,
            vence_en=caso.plazo.vence_en,
            horas_restantes=caso.plazo.horas_restantes,
        ),
        "acciones": list(caso.acciones),
    }


class PaginaDeCasosResponse(PaginaResponse[CasoResumenResponse]):
    @classmethod
    def desde_dominio(cls, pagina: Pagina[CasoResumen]) -> Self:
        return cls(
            items=[CasoResumenResponse.desde_dominio(caso) for caso in pagina.items],
            siguiente=pagina.siguiente,
            hay_mas=pagina.hay_mas,
        )


class ConteoAcotadoResponse(ApiModel):
    cantidad: int
    con_mas: bool

    @classmethod
    def desde_dominio(cls, conteo: ConteoAcotado) -> Self:
        return cls(cantidad=conteo.cantidad, con_mas=conteo.con_mas)


class ConteoPorEstadoResponse(ApiModel):
    registrado: ConteoAcotadoResponse
    clasificado: ConteoAcotadoResponse
    derivado: ConteoAcotadoResponse
    en_gestion: ConteoAcotadoResponse = Field(alias="en-gestion")
    resuelto: ConteoAcotadoResponse
    archivado: ConteoAcotadoResponse


class ConteosDeCasosResponse(ApiModel):
    todos: ConteoAcotadoResponse
    total: ConteoAcotadoResponse
    por_estado: ConteoPorEstadoResponse

    @classmethod
    def desde_dominio(cls, conteos: ConteosDeCasos) -> Self:
        por_estado = conteos.por_estado
        return cls(
            todos=ConteoAcotadoResponse.desde_dominio(conteos.todos),
            total=ConteoAcotadoResponse.desde_dominio(conteos.total),
            por_estado=ConteoPorEstadoResponse.model_validate(
                {estado.value: ConteoAcotadoResponse.desde_dominio(conteo) for estado, conteo in por_estado.items()}
            ),
        )


class CasosPorVencerResponse(ApiModel):
    total: int
    por_vencer: int
    vencidos: int
    casos: list[CasoResumenResponse]

    @classmethod
    def desde_dominio(cls, resumen: CasosPorVencer) -> Self:
        return cls(
            total=resumen.total,
            por_vencer=resumen.por_vencer,
            vencidos=resumen.vencidos,
            casos=[CasoResumenResponse.desde_dominio(caso) for caso in resumen.casos],
        )
