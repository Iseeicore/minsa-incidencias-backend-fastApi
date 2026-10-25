from typing import TYPE_CHECKING, Annotated, Self

from pydantic import AfterValidator, Field, StrictBool, StrictStr, StringConstraints

from app.constants.filtro_corrupcion import (
    ALIAS_POR_ENTIDAD_MAXIMO,
    CODIGO_DE_ENTIDAD_MAXIMO,
    ENTIDADES_EVALUACION_MAXIMO,
    NOMBRE_DE_ENTIDAD_MAXIMO,
    TEXTO_EVALUACION_MAXIMO,
)
from app.constants.textos.filtro_corrupcion import mensaje_texto_demasiado_largo
from app.enums.acuerdo_reglas_ia import AcuerdoReglasIa
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.certeza_corrupcion import CertezaCorrupcion
from app.enums.faltante_corrupcion import FaltanteCorrupcion
from app.enums.nivel_cargo import NivelCargo
from app.enums.origen_propuesta import OrigenPropuesta
from app.enums.senal_sensible import SenalSensible
from app.enums.tipo_contacto import TipoContacto
from app.enums.tipo_entidad import TipoEntidad
from app.enums.tipo_senal import TipoSenal
from app.enums.via_entidad import ViaEntidad
from app.filtro_corrupcion.application.evaluar_corrupcion import SolicitudDeEvaluacion
from app.filtro_corrupcion.domain.tipos import ContextoEvaluacion, EntidadCatalogo
from app.shared.api_model import ApiModel
from app.shared.texto_js import longitud_como_js

if TYPE_CHECKING:
    from app.filtro_corrupcion.domain.tipos import (
        DestinoSiTitular,
        EntidadDetectada,
        EvaluacionDeCorrupcion,
        IdentidadDetectada,
        ReferenciaDerivacion,
        ResultadoCombinacion,
        ResultadoCorrupcion,
        TitularDetectado,
    )

type Numero = int | float


def _texto_corto(valor: str) -> str:
    if longitud_como_js(valor) > TEXTO_EVALUACION_MAXIMO:
        raise ValueError(mensaje_texto_demasiado_largo(TEXTO_EVALUACION_MAXIMO))
    return valor


Texto = Annotated[StrictStr, AfterValidator(_texto_corto)]
Recortado = Annotated[StrictStr, StringConstraints(strip_whitespace=True, min_length=1)]
Peso = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class EntidadRequest(ApiModel):
    codigo: Annotated[Recortado, StringConstraints(max_length=CODIGO_DE_ENTIDAD_MAXIMO)]
    nombre: Annotated[Recortado, StringConstraints(max_length=NOMBRE_DE_ENTIDAD_MAXIMO)]
    alias: list[Annotated[Recortado, StringConstraints(max_length=NOMBRE_DE_ENTIDAD_MAXIMO)]] | None = Field(
        default=None, max_length=ALIAS_POR_ENTIDAD_MAXIMO
    )

    def a_dominio(self) -> EntidadCatalogo:
        return EntidadCatalogo(self.codigo, self.nombre, alias=tuple(self.alias or ()))


class EvaluacionRequest(ApiModel):
    texto: Texto
    entidades: list[EntidadRequest] | None = Field(default=None, max_length=ENTIDADES_EVALUACION_MAXIMO)
    establecimiento_conocido: StrictBool | None = None
    tiene_archivos: StrictBool | None = None
    peso_ia: Peso | None = None

    def a_solicitud(self) -> SolicitudDeEvaluacion:
        entidades = tuple(entidad.a_dominio() for entidad in self.entidades) if self.entidades is not None else None
        contexto = ContextoEvaluacion(
            entidades=entidades,
            establecimiento_conocido=self.establecimiento_conocido is True,
            tiene_archivos=self.tiene_archivos is True,
        )
        return SolicitudDeEvaluacion(
            texto=self.texto,
            contexto=contexto,
            combinar_con_ia="peso_ia" in self.model_fields_set,
            peso_ia=self.peso_ia,
        )


class SenalResponse(ApiModel):
    frase: str
    tipo: TipoSenal
    peso: int


class ActorResponse(ApiModel):
    cargo: str
    nivel: NivelCargo


class EntidadDetectadaResponse(ApiModel):
    codigo: str
    nombre: str
    tipo: TipoEntidad | None

    @classmethod
    def desde_dominio(cls, entidad: EntidadDetectada) -> Self:
        return cls(codigo=entidad.codigo, nombre=entidad.nombre, tipo=entidad.tipo)


class TitularDetectadoResponse(ApiModel):
    cargo: str
    es_equivalente_del_maximo: bool
    nombre_coincide: bool

    @classmethod
    def desde_dominio(cls, titular: TitularDetectado) -> Self:
        return cls(
            cargo=titular.cargo,
            es_equivalente_del_maximo=titular.es_equivalente_del_maximo,
            nombre_coincide=titular.nombre_coincide,
        )


class UbicacionDetectadaResponse(ApiModel):
    zona: str
    codigo_entidad: str


class IdentidadResponse(ApiModel):
    puntos: int
    entidad: EntidadDetectadaResponse | None
    via_entidad: ViaEntidad | None
    titular: TitularDetectadoResponse | None
    nombre_coincide: bool
    ubicacion: UbicacionDetectadaResponse | None

    @classmethod
    def desde_dominio(cls, identidad: IdentidadDetectada) -> Self:
        ubicacion = identidad.ubicacion
        return cls(
            puntos=identidad.puntos,
            entidad=_entidad(identidad.entidad),
            via_entidad=identidad.via_entidad,
            titular=_titular(identidad.titular),
            nombre_coincide=identidad.nombre_coincide,
            ubicacion=UbicacionDetectadaResponse(zona=ubicacion.zona, codigo_entidad=ubicacion.codigo_entidad)
            if ubicacion is not None
            else None,
        )


class DestinoSiTitularResponse(ApiModel):
    texto: str
    entidad_destino_codigo: str | None

    @classmethod
    def desde_dominio(cls, destino: DestinoSiTitular) -> Self:
        return cls(texto=destino.texto, entidad_destino_codigo=destino.entidad_destino_codigo)


class ReferenciaDerivacionResponse(ApiModel):
    codigo_entidad: str
    contactos_disponibles: list[TipoContacto]
    destino_si_titular: DestinoSiTitularResponse | None
    aplica_al_titular: bool

    @classmethod
    def desde_dominio(cls, referencia: ReferenciaDerivacion) -> Self:
        destino = referencia.destino_si_titular
        return cls(
            codigo_entidad=referencia.codigo_entidad,
            contactos_disponibles=list(referencia.contactos_disponibles),
            destino_si_titular=DestinoSiTitularResponse.desde_dominio(destino) if destino is not None else None,
            aplica_al_titular=referencia.aplica_al_titular,
        )


class CombinacionResponse(ApiModel):
    propuesta_corrupcion: bool
    puntaje_reglas: int
    peso_ia: int | None
    puntaje_total: int
    umbral: int
    subida_por_ia: bool
    acuerdo: AcuerdoReglasIa
    confianza: float
    requiere_otrans: bool
    revision_otrans: bool
    requiere_revision_humana: bool

    @classmethod
    def desde_dominio(cls, combinacion: ResultadoCombinacion) -> Self:
        return cls(
            propuesta_corrupcion=combinacion.propuesta_corrupcion,
            puntaje_reglas=combinacion.puntaje_reglas,
            peso_ia=combinacion.peso_ia,
            puntaje_total=combinacion.puntaje_total,
            umbral=combinacion.umbral,
            subida_por_ia=combinacion.subida_por_ia,
            acuerdo=combinacion.acuerdo,
            confianza=combinacion.confianza,
            requiere_otrans=combinacion.requiere_otrans,
            revision_otrans=combinacion.revision_otrans,
            requiere_revision_humana=combinacion.requiere_revision_humana,
        )


def _entidad(entidad: EntidadDetectada | None) -> EntidadDetectadaResponse | None:
    return EntidadDetectadaResponse.desde_dominio(entidad) if entidad is not None else None


def _titular(titular: TitularDetectado | None) -> TitularDetectadoResponse | None:
    return TitularDetectadoResponse.desde_dominio(titular) if titular is not None else None


class EvaluacionCorrupcionResponse(ApiModel):
    aplica: bool
    puntaje: int
    certeza: CertezaCorrupcion
    propuesta_corrupcion: bool
    origen_propuesta: OrigenPropuesta | None
    senales: list[SenalResponse]
    actor: ActorResponse | None
    nombre_mencionado: str | None
    entidad: EntidadDetectadaResponse | None
    identidad: IdentidadResponse
    titular: TitularDetectadoResponse | None
    faltantes: list[FaltanteCorrupcion]
    requiere_otrans: bool
    referencia_derivacion: ReferenciaDerivacionResponse | None
    requiere_segunda_opinion: bool
    senal_sensible: SenalSensible | None
    categoria_sugerida: CategoriaIncidencia | None
    escalar_a_otrans: bool
    version_reglas: str
    combinacion: CombinacionResponse | None = None

    @classmethod
    def desde_dominio(cls, evaluacion: EvaluacionDeCorrupcion) -> Self:
        resultado = evaluacion.resultado
        campos = _campos_del_resultado(resultado)
        if evaluacion.combinacion is None:
            return cls(**campos)
        return cls(**campos, combinacion=CombinacionResponse.desde_dominio(evaluacion.combinacion))


def _campos_del_resultado(resultado: ResultadoCorrupcion) -> dict[str, object]:
    referencia = resultado.referencia_derivacion
    actor = resultado.actor
    return {
        "aplica": resultado.aplica,
        "puntaje": resultado.puntaje,
        "certeza": resultado.certeza,
        "propuesta_corrupcion": resultado.propuesta_corrupcion,
        "origen_propuesta": resultado.origen_propuesta,
        "senales": [SenalResponse(frase=s.frase, tipo=s.tipo, peso=s.peso) for s in resultado.senales],
        "actor": ActorResponse(cargo=actor.cargo, nivel=actor.nivel) if actor is not None else None,
        "nombre_mencionado": resultado.nombre_mencionado,
        "entidad": _entidad(resultado.entidad),
        "identidad": IdentidadResponse.desde_dominio(resultado.identidad),
        "titular": _titular(resultado.titular),
        "faltantes": list(resultado.faltantes),
        "requiere_otrans": resultado.requiere_otrans,
        "referencia_derivacion": ReferenciaDerivacionResponse.desde_dominio(referencia)
        if referencia is not None
        else None,
        "requiere_segunda_opinion": resultado.requiere_segunda_opinion,
        "senal_sensible": resultado.senal_sensible,
        "categoria_sugerida": resultado.categoria_sugerida,
        "escalar_a_otrans": resultado.escalar_a_otrans,
        "version_reglas": resultado.version_reglas,
    }
