from typing import TYPE_CHECKING, Self

from app.enums.categoria_api import CategoriaApi
from app.enums.grupo_cita import GrupoCita
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.enums.tipo_contacto import TipoContacto
from app.enums.variante_ia import VarianteIa
from app.shared.api_model import ApiModel

if TYPE_CHECKING:
    from app.incidencias.domain.analisis import (
        AnalisisDeIncidencia,
        CitaDeNorma,
        DestinoSiTitular,
        FichaDeDerivacion,
    )

type Numero = int | float


class SenalResponse(ApiModel):
    frase: str
    tipo: str
    peso: Numero


class CitaNormaResponse(ApiModel):
    fragmento_id: str
    grupo: GrupoCita
    referencia: str
    titulo: str
    texto: str | None
    senales_que_la_motivan: list[str]

    @classmethod
    def desde_dominio(cls, cita: CitaDeNorma) -> Self:
        return cls(
            fragmento_id=cita.fragmento_id,
            grupo=cita.grupo,
            referencia=cita.referencia,
            titulo=cita.titulo,
            texto=cita.texto,
            senales_que_la_motivan=list(cita.senales_que_la_motivan),
        )


class RequisitoFaltanteResponse(ApiModel):
    codigo: str
    referencia: str
    texto: str


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
    def desde_dominio(cls, ficha: FichaDeDerivacion) -> Self:
        destino = ficha.destino_si_titular
        return cls(
            codigo_entidad=ficha.codigo_entidad,
            contactos_disponibles=list(ficha.contactos_disponibles),
            destino_si_titular=DestinoSiTitularResponse.desde_dominio(destino) if destino is not None else None,
            aplica_al_titular=ficha.aplica_al_titular,
        )


class AreaMencionadaResponse(ApiModel):
    codigo: str
    nombre: str


class ModeloResponse(ApiModel):
    variante: VarianteIa | None
    degradado: bool
    peso_ia: Numero | None


class AnalisisIaResponse(ApiModel):
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
    senales: list[SenalResponse]
    supuestos: list[CitaNormaResponse]
    procedimiento: list[CitaNormaResponse]
    sin_supuesto_identificado: bool
    etiqueta_normas: str
    version_normas: str | None
    transcripcion_anexo_c_cotejada: bool
    requisitos_faltantes: list[RequisitoFaltanteResponse]
    ficha_derivacion: ReferenciaDerivacionResponse | None
    cargo_mencionado: str | None
    nombre_mencionado: str | None
    area_mencionada: AreaMencionadaResponse | None
    modelo: ModeloResponse
    fecha_analisis: str

    @classmethod
    def desde_dominio(cls, analisis: AnalisisDeIncidencia) -> Self:
        area = analisis.area_mencionada
        ficha = analisis.ficha_derivacion
        return cls(
            codigo=analisis.codigo,
            categoria_ia=analisis.categoria_ia,
            confianza_ia=analisis.confianza_ia,
            version_clasificador=analisis.version_clasificador,
            version_reglas=analisis.version_reglas,
            puntaje=analisis.puntaje,
            motivo_de_escritura=analisis.motivo_de_escritura,
            propuesta_del_analisis=analisis.propuesta_del_analisis,
            requiere_revision_humana=analisis.requiere_revision_humana,
            escalar_a_otrans=analisis.escalar_a_otrans,
            explicacion=analisis.explicacion,
            senales=[SenalResponse(frase=s.frase, tipo=s.tipo, peso=s.peso) for s in analisis.senales],
            supuestos=[CitaNormaResponse.desde_dominio(cita) for cita in analisis.supuestos],
            procedimiento=[CitaNormaResponse.desde_dominio(cita) for cita in analisis.procedimiento],
            sin_supuesto_identificado=analisis.sin_supuesto_identificado,
            etiqueta_normas=analisis.etiqueta_normas,
            version_normas=analisis.version_normas,
            transcripcion_anexo_c_cotejada=analisis.transcripcion_anexo_c_cotejada,
            requisitos_faltantes=[
                RequisitoFaltanteResponse(codigo=r.codigo, referencia=r.referencia, texto=r.texto)
                for r in analisis.requisitos_faltantes
            ],
            ficha_derivacion=ReferenciaDerivacionResponse.desde_dominio(ficha) if ficha is not None else None,
            cargo_mencionado=analisis.cargo_mencionado,
            nombre_mencionado=analisis.nombre_mencionado,
            area_mencionada=AreaMencionadaResponse(codigo=area.codigo, nombre=area.nombre)
            if area is not None
            else None,
            modelo=ModeloResponse(
                variante=analisis.modelo.variante, degradado=analisis.modelo.degradado, peso_ia=analisis.modelo.peso_ia
            ),
            fecha_analisis=analisis.fecha_analisis,
        )
