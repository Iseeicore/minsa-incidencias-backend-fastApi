from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


@dataclass(frozen=True, slots=True)
class TitularCatalogo:
    cargo: str
    nombre: str | None


@dataclass(frozen=True, slots=True)
class DestinoSiTitular:
    texto: str
    entidad_destino_codigo: str | None


@dataclass(frozen=True, slots=True)
class EntidadCatalogo:
    codigo: str
    nombre: str
    tipo: TipoEntidad | None = None
    alias: tuple[str, ...] = ()
    alias_derivados: tuple[str, ...] = ()
    titular: TitularCatalogo | None = None
    destino_si_titular: DestinoSiTitular | None = None
    contactos_disponibles: tuple[TipoContacto, ...] = ()


@dataclass(frozen=True, slots=True)
class UbicacionEntidad:
    zona: str
    codigo_entidad: str
    ambigua_con_establecimiento: bool


@dataclass(frozen=True, slots=True)
class ContextoEvaluacion:
    entidades: tuple[EntidadCatalogo, ...] | None = None
    establecimiento_conocido: bool = False
    tiene_archivos: bool = False


@dataclass(frozen=True, slots=True)
class SenalDetectada:
    frase: str
    tipo: TipoSenal
    peso: int


@dataclass(frozen=True, slots=True)
class ActorDetectado:
    cargo: str
    nivel: NivelCargo


@dataclass(frozen=True, slots=True)
class EntidadDetectada:
    codigo: str
    nombre: str
    tipo: TipoEntidad | None


@dataclass(frozen=True, slots=True)
class UbicacionDetectada:
    zona: str
    codigo_entidad: str


@dataclass(frozen=True, slots=True)
class TitularDetectado:
    cargo: str
    es_equivalente_del_maximo: bool
    nombre_coincide: bool


@dataclass(frozen=True, slots=True)
class IdentidadDetectada:
    puntos: int = 0
    entidad: EntidadDetectada | None = None
    via_entidad: ViaEntidad | None = None
    titular: TitularDetectado | None = None
    nombre_coincide: bool = False
    ubicacion: UbicacionDetectada | None = None


@dataclass(frozen=True, slots=True)
class ReferenciaDerivacion:
    codigo_entidad: str
    contactos_disponibles: tuple[TipoContacto, ...]
    destino_si_titular: DestinoSiTitular | None
    aplica_al_titular: bool


@dataclass(frozen=True, slots=True)
class ResultadoCorrupcion:
    aplica: bool
    puntaje: int
    certeza: CertezaCorrupcion
    propuesta_corrupcion: bool
    origen_propuesta: OrigenPropuesta | None
    senales: tuple[SenalDetectada, ...]
    actor: ActorDetectado | None
    nombre_mencionado: str | None
    entidad: EntidadDetectada | None
    identidad: IdentidadDetectada
    titular: TitularDetectado | None
    faltantes: tuple[FaltanteCorrupcion, ...]
    requiere_otrans: bool
    referencia_derivacion: ReferenciaDerivacion | None
    requiere_segunda_opinion: bool
    senal_sensible: SenalSensible | None
    categoria_sugerida: CategoriaIncidencia | None
    escalar_a_otrans: bool
    version_reglas: str


@dataclass(frozen=True, slots=True)
class ResultadoCombinacion:
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


@dataclass(frozen=True, slots=True)
class EvaluacionDeCorrupcion:
    resultado: ResultadoCorrupcion
    combinacion: ResultadoCombinacion | None = field(default=None)
