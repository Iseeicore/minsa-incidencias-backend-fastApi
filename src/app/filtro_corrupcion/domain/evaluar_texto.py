from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants.filtro_corrupcion import (
    LONGITUD_MINIMA_TEXTO_CORRUPCION,
    PESO_POR_TIPO,
    PUNTOS_IDENTIDAD_PARA_OTRANS,
    PUNTOS_NOMBRE_TITULAR,
    PUNTOS_UBICACION,
    TIPOS_DE_SENAL_DE_CORRUPCION,
    TIPOS_DE_SENAL_DE_IDENTIDAD,
    TOPE_PUNTOS_IDENTIDAD,
    UMBRAL_CERTEZA_ALTA,
    UMBRAL_CERTEZA_MEDIA,
    VERSION_REGLAS_CORRUPCION,
)
from app.enums.certeza_corrupcion import CertezaCorrupcion
from app.enums.faltante_corrupcion import FaltanteCorrupcion
from app.enums.nivel_cargo import NivelCargo
from app.enums.origen_propuesta import OrigenPropuesta
from app.enums.tipo_senal import TipoSenal
from app.enums.via_entidad import ViaEntidad
from app.filtro_corrupcion.domain.catalogo import catalogo_de_entidades
from app.filtro_corrupcion.domain.coincidencias import buscar_coincidencias
from app.filtro_corrupcion.domain.deteccion_de_identidad import (
    EntidadHallada,
    TitularNombrado,
    UbicacionHallada,
    detectar_entidad,
    detectar_nombre_mencionado,
    detectar_titular,
    detectar_titular_nombrado,
    detectar_ubicacion,
    entidad_detectada_de,
    referencia_de,
    titular_por_su_nombre,
)
from app.filtro_corrupcion.domain.deteccion_de_senales import (
    AcosoDetectado,
    detectar_acoso,
    detectar_actor,
    detectar_senales,
    es_jefatura,
    hay_verbo_de_cobro,
)
from app.filtro_corrupcion.domain.lexico import indice_de_pruebas
from app.filtro_corrupcion.domain.normalizar_texto import marcar_montos, tokenizar
from app.filtro_corrupcion.domain.tipos import (
    ActorDetectado,
    ContextoEvaluacion,
    EntidadDetectada,
    IdentidadDetectada,
    ResultadoCorrupcion,
    SenalDetectada,
    TitularDetectado,
)
from app.shared.texto_js import longitud_como_js, recortar_como_js

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.filtro_corrupcion.domain.tipos import EntidadCatalogo


@dataclass(frozen=True, slots=True)
class Hallazgos:
    actor: tuple[ActorDetectado, SenalDetectada] | None
    por_alias: EntidadHallada | None
    titular_nombrado: TitularNombrado | None
    catalogo: EntidadCatalogo | None
    ubicacion: UbicacionHallada | None
    titular: TitularDetectado | None
    titular_de_identidad: TitularDetectado | None
    nombre_mencionado: str | None

    @property
    def nombre_coincide(self) -> bool:
        return self.titular_nombrado is not None

    @property
    def entidad(self) -> EntidadDetectada | None:
        return entidad_detectada_de(self.catalogo) if self.catalogo is not None else None

    @property
    def via_entidad(self) -> ViaEntidad | None:
        if self.por_alias is not None:
            return ViaEntidad.NOMBRE_O_ALIAS
        return ViaEntidad.NOMBRE_TITULAR if self.titular_nombrado is not None else None

    @property
    def actor_detectado(self) -> ActorDetectado | None:
        return self.actor[0] if self.actor is not None else None


def aporte_de_identidad(senales: Sequence[SenalDetectada]) -> int:
    suma = sum(senal.peso for senal in senales if senal.tipo in TIPOS_DE_SENAL_DE_IDENTIDAD)
    return min(suma, TOPE_PUNTOS_IDENTIDAD)


def puntos_de_identidad(
    *, hay_entidad_nombrada: bool, hay_cargo: bool, nombre_coincide: bool, hay_ubicacion: bool
) -> int:
    suma = (
        (PESO_POR_TIPO[TipoSenal.ENTIDAD] if hay_entidad_nombrada else 0)
        + (PESO_POR_TIPO[TipoSenal.ACTOR] if hay_cargo else 0)
        + (PUNTOS_NOMBRE_TITULAR if nombre_coincide else 0)
        + (PUNTOS_UBICACION if hay_ubicacion else 0)
    )
    return min(suma, TOPE_PUNTOS_IDENTIDAD)


def _certeza_de(puntaje: int, *, propuesta_corrupcion: bool) -> CertezaCorrupcion:
    if not propuesta_corrupcion:
        return CertezaCorrupcion.BAJA
    return CertezaCorrupcion.ALTA if puntaje >= UMBRAL_CERTEZA_ALTA else CertezaCorrupcion.MEDIA


def _es_zona_gris(*, propuesta_corrupcion: bool, hay_entidad: bool, hallazgos: Hallazgos, palabras: list[str]) -> bool:
    if propuesta_corrupcion or not hay_entidad:
        return False
    actor = hallazgos.actor_detectado
    nombra_jefatura = (
        hallazgos.titular_de_identidad is not None
        or (actor is not None and actor.nivel == NivelCargo.CARGO_MAXIMO)
        or es_jefatura(palabras)
    )
    return nombra_jefatura and hay_verbo_de_cobro(palabras)


def _hallazgos(
    palabras: list[str], recortado: str, entidades: tuple[EntidadCatalogo, ...], contexto: ContextoEvaluacion
) -> Hallazgos:
    actor = detectar_actor(palabras)
    por_alias = detectar_entidad(palabras, entidades)
    titular_nombrado = detectar_titular_nombrado(
        palabras, entidades, por_alias.catalogo if por_alias is not None else None
    )
    catalogo = (
        por_alias.catalogo if por_alias is not None else (titular_nombrado.catalogo if titular_nombrado else None)
    )
    ubicacion = (
        None
        if catalogo is not None
        else detectar_ubicacion(palabras, entidades, establecimiento_conocido=contexto.establecimiento_conocido)
    )
    titular = detectar_titular(actor[0] if actor is not None else None, nombre_coincide=titular_nombrado is not None)
    titular_de_identidad = titular or (titular_por_su_nombre(titular_nombrado.catalogo) if titular_nombrado else None)
    return Hallazgos(
        actor=actor,
        por_alias=por_alias,
        titular_nombrado=titular_nombrado,
        catalogo=catalogo,
        ubicacion=ubicacion,
        titular=titular,
        titular_de_identidad=titular_de_identidad,
        nombre_mencionado=detectar_nombre_mencionado(recortado),
    )


def _senales_de(palabras: list[str], hallazgos: Hallazgos) -> list[SenalDetectada]:
    senales = detectar_senales(palabras)
    if hallazgos.actor is not None:
        senales.append(hallazgos.actor[1])
    if hallazgos.por_alias is not None:
        senales.append(hallazgos.por_alias.senal)
    if hallazgos.titular_nombrado is not None:
        senales.append(
            SenalDetectada(hallazgos.titular_nombrado.frase, TipoSenal.NOMBRE_TITULAR, PUNTOS_NOMBRE_TITULAR)
        )
    if hallazgos.ubicacion is not None:
        senales.append(hallazgos.ubicacion.senal)
    return senales


def _identidad_de(palabras: list[str], hallazgos: Hallazgos) -> IdentidadDetectada:
    puntos = puntos_de_identidad(
        hay_entidad_nombrada=hallazgos.por_alias is not None,
        hay_cargo=hallazgos.titular is not None or es_jefatura(palabras),
        nombre_coincide=hallazgos.nombre_coincide,
        hay_ubicacion=hallazgos.ubicacion is not None,
    )
    return IdentidadDetectada(
        puntos=puntos,
        entidad=hallazgos.entidad,
        via_entidad=hallazgos.via_entidad,
        titular=hallazgos.titular_de_identidad,
        nombre_coincide=hallazgos.nombre_coincide,
        ubicacion=hallazgos.ubicacion.ubicacion if hallazgos.ubicacion is not None else None,
    )


def _faltantes_de(
    palabras: list[str], hallazgos: Hallazgos, contexto: ContextoEvaluacion
) -> tuple[FaltanteCorrupcion, ...]:
    faltantes: list[FaltanteCorrupcion] = []
    if hallazgos.actor is None and not hallazgos.nombre_mencionado and not hallazgos.nombre_coincide:
        faltantes.append(FaltanteCorrupcion.AUTOR_O_CARGO)
    if hallazgos.entidad is None and not contexto.establecimiento_conocido:
        faltantes.append(FaltanteCorrupcion.ENTIDAD)
    if not contexto.tiene_archivos and not buscar_coincidencias(palabras, indice_de_pruebas()):
        faltantes.append(FaltanteCorrupcion.PRUEBAS)
    return tuple(faltantes)


def _sin_datos() -> ResultadoCorrupcion:
    acoso = AcosoDetectado()
    return ResultadoCorrupcion(
        aplica=False,
        puntaje=0,
        certeza=CertezaCorrupcion.BAJA,
        propuesta_corrupcion=False,
        origen_propuesta=None,
        senales=(),
        actor=None,
        nombre_mencionado=None,
        entidad=None,
        identidad=IdentidadDetectada(),
        titular=None,
        faltantes=(FaltanteCorrupcion.DATOS_INSUFICIENTES,),
        requiere_otrans=False,
        referencia_derivacion=None,
        requiere_segunda_opinion=False,
        senal_sensible=acoso.senal_sensible,
        categoria_sugerida=acoso.categoria_sugerida,
        escalar_a_otrans=acoso.escalar_a_otrans,
        version_reglas=VERSION_REGLAS_CORRUPCION,
    )


def evaluar_texto_corrupcion(texto: str, contexto: ContextoEvaluacion | None = None) -> ResultadoCorrupcion:
    contexto = contexto or ContextoEvaluacion()
    recortado = recortar_como_js(texto)
    if longitud_como_js(recortado) < LONGITUD_MINIMA_TEXTO_CORRUPCION:
        return _sin_datos()
    palabras = marcar_montos(tokenizar(recortado))
    entidades = contexto.entidades if contexto.entidades is not None else catalogo_de_entidades()
    hallazgos = _hallazgos(palabras, recortado, entidades, contexto)
    senales = _senales_de(palabras, hallazgos)
    puntaje = sum(s.peso for s in senales if s.tipo not in TIPOS_DE_SENAL_DE_IDENTIDAD) + aporte_de_identidad(senales)
    hay_evidencia = any(s.tipo in TIPOS_DE_SENAL_DE_CORRUPCION for s in senales)
    propuesta_por_reglas = hay_evidencia and puntaje >= UMBRAL_CERTEZA_MEDIA
    identidad = _identidad_de(palabras, hallazgos)
    zona_gris = _es_zona_gris(
        propuesta_corrupcion=propuesta_por_reglas,
        hay_entidad=hallazgos.entidad is not None,
        hallazgos=hallazgos,
        palabras=palabras,
    )
    hay_negativa_decisiva = any(s.tipo == TipoSenal.NEGATIVA_DECISIVA for s in senales)
    hay_indicio = hay_evidencia or zona_gris or hay_verbo_de_cobro(palabras)
    propuesta_por_identidad = (
        not propuesta_por_reglas
        and not hay_negativa_decisiva
        and hay_indicio
        and identidad.puntos >= PUNTOS_IDENTIDAD_PARA_OTRANS
    )
    propuesta_corrupcion = propuesta_por_reglas or propuesta_por_identidad
    acoso = detectar_acoso(palabras, hallazgos.actor_detectado, hallazgos.titular)
    return ResultadoCorrupcion(
        aplica=True,
        puntaje=puntaje,
        certeza=CertezaCorrupcion.BAJA
        if propuesta_por_identidad
        else _certeza_de(puntaje, propuesta_corrupcion=propuesta_por_reglas),
        propuesta_corrupcion=propuesta_corrupcion,
        origen_propuesta=_origen_de(
            propuesta_por_reglas=propuesta_por_reglas, propuesta_por_identidad=propuesta_por_identidad
        ),
        senales=tuple(senales),
        actor=hallazgos.actor_detectado,
        nombre_mencionado=hallazgos.nombre_mencionado,
        entidad=hallazgos.entidad,
        identidad=identidad,
        titular=hallazgos.titular,
        faltantes=_faltantes_de(palabras, hallazgos, contexto) if propuesta_corrupcion else (),
        requiere_otrans=propuesta_corrupcion,
        referencia_derivacion=referencia_de(hallazgos.catalogo, hallazgos.titular_de_identidad)
        if propuesta_corrupcion and hallazgos.catalogo is not None
        else None,
        requiere_segunda_opinion=zona_gris,
        senal_sensible=acoso.senal_sensible,
        categoria_sugerida=acoso.categoria_sugerida,
        escalar_a_otrans=acoso.escalar_a_otrans,
        version_reglas=VERSION_REGLAS_CORRUPCION,
    )


def _origen_de(*, propuesta_por_reglas: bool, propuesta_por_identidad: bool) -> OrigenPropuesta | None:
    if propuesta_por_reglas:
        return OrigenPropuesta.REGLAS
    return OrigenPropuesta.IDENTIDAD if propuesta_por_identidad else None
