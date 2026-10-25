from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from app.enums.categoria_api import CategoriaApi
    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.grupo_cita import GrupoCita
    from app.enums.motivo_de_escritura import MotivoDeEscritura
    from app.enums.tipo_contacto import TipoContacto
    from app.enums.variante_ia import VarianteIa

type Numero = int | float


@dataclass(frozen=True, slots=True)
class FilaAnalisis:
    version_reglas: str
    puntaje: int
    senales: object
    cargo_mencionado: str | None
    nombre_mencionado: str | None
    area_mencionada_codigo: str | None
    area_mencionada_nombre: str | None
    categoria_ia: CategoriaIncidencia | None
    confianza_ia: float | None
    version_clasificador: str | None
    fecha_analisis: datetime


@dataclass(frozen=True, slots=True)
class SenalDeAnalisis:
    frase: str
    tipo: str
    peso: Numero


@dataclass(frozen=True, slots=True)
class CitaGuardada:
    fragmento_id: str
    referencia: str
    grupo: GrupoCita
    senales_que_la_motivan: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NormasGuardadas:
    version: str
    transcripcion_anexo_c_cotejada: bool
    sin_supuesto_identificado: bool
    citas: tuple[CitaGuardada, ...]


@dataclass(frozen=True, slots=True)
class DecisionGuardada:
    motivo: MotivoDeEscritura
    propuesta_del_analisis: CategoriaIncidencia | None
    escalar_a_otrans: bool
    requiere_revision_humana: bool
    peso_ia: Numero | None


@dataclass(frozen=True, slots=True)
class ModeloGuardado:
    variante: VarianteIa | None
    degradado: bool


@dataclass(frozen=True, slots=True)
class DestinoSiTitular:
    texto: str
    entidad_destino_codigo: str | None


@dataclass(frozen=True, slots=True)
class FichaDeDerivacion:
    codigo_entidad: str
    contactos_disponibles: tuple[TipoContacto, ...]
    destino_si_titular: DestinoSiTitular | None
    aplica_al_titular: bool


@dataclass(frozen=True, slots=True)
class CitaDeNorma:
    fragmento_id: str
    grupo: GrupoCita
    referencia: str
    titulo: str
    texto: str | None
    senales_que_la_motivan: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RequisitoFaltante:
    codigo: str
    referencia: str
    texto: str


@dataclass(frozen=True, slots=True)
class AreaMencionada:
    codigo: str
    nombre: str


@dataclass(frozen=True, slots=True)
class ModeloDelAnalisis:
    variante: VarianteIa | None
    degradado: bool
    peso_ia: Numero | None


@dataclass(frozen=True, slots=True)
class AnalisisDeIncidencia:
    codigo: str
    categoria_ia: CategoriaApi | None
    confianza_ia: float | None
    version_clasificador: str | None
    version_reglas: str
    puntaje: int
    motivo_de_escritura: MotivoDeEscritura | None
    propuesta_del_analisis: CategoriaApi | None
    requiere_revision_humana: bool
    escalar_a_otrans: bool
    explicacion: str | None
    senales: tuple[SenalDeAnalisis, ...]
    supuestos: tuple[CitaDeNorma, ...]
    procedimiento: tuple[CitaDeNorma, ...]
    sin_supuesto_identificado: bool
    etiqueta_normas: str
    version_normas: str | None
    transcripcion_anexo_c_cotejada: bool
    requisitos_faltantes: tuple[RequisitoFaltante, ...]
    ficha_derivacion: FichaDeDerivacion | None
    cargo_mencionado: str | None
    nombre_mencionado: str | None
    area_mencionada: AreaMencionada | None
    modelo: ModeloDelAnalisis
    fecha_analisis: str
