from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

from app.constants.mapa_senal_fragmento import MAPA_SENAL_FRAGMENTO
from app.constants.normas import ETIQUETA_REFERENCIA_ORIENTATIVA, TRANSCRIPCION_ANEXO_C_COTEJADA, VERSION_DE_NORMAS
from app.constants.trazabilidad_normas import (
    FRAGMENTO_DE_DEFINICION_DE_RECLAMO,
    FRAGMENTO_DE_DERIVACION_DE_QUEJAS_Y_RECLAMOS,
    FRAGMENTOS_DE_PROCEDIMIENTO_SI_HAY_CORRUPCION,
    MAXIMO_SUPUESTOS_CITADOS,
    REQUISITO_POR_FALTANTE,
    SENALES_QUE_PUEDEN_CITAR_UN_SUPUESTO,
)
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.grupo_cita import GrupoCita
from app.filtro_corrupcion.domain.coincidencias import (
    EntradaPonderada,
    Indice,
    ItemCompilado,
    buscar_coincidencias,
    compilar_plantilla,
    crear_indice,
)
from app.filtro_corrupcion.domain.normalizar_texto import tokenizar
from app.shared.normas import FragmentoNorma, fragmentos_por_id

if TYPE_CHECKING:
    from collections.abc import Mapping

    from app.enums.tema_norma import TemaNorma
    from app.filtro_corrupcion.domain.tipos import ResultadoCorrupcion


@dataclass(frozen=True, slots=True)
class TemaDeNorma:
    tema: TemaNorma
    descripcion: str
    plantillas: tuple[str, ...]
    fragmentos: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class EntradaDeTema(EntradaPonderada):
    tema: TemaDeNorma


@dataclass(frozen=True, slots=True)
class CitaDeNormaClasificada:
    fragmento_id: str
    referencia: str
    grupo: GrupoCita
    senales_que_la_motivan: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TrazabilidadDeNormas:
    version: str
    etiqueta: str
    supuestos: tuple[CitaDeNormaClasificada, ...]
    procedimiento: tuple[CitaDeNormaClasificada, ...]
    sin_supuesto_identificado: bool
    transcripcion_anexo_c_cotejada: bool


@dataclass(frozen=True, slots=True)
class TemaCoincidente:
    tema: TemaDeNorma
    frases: tuple[str, ...]


@cache
def temas_de_norma() -> tuple[TemaDeNorma, ...]:
    return tuple(TemaDeNorma(*dato) for dato in MAPA_SENAL_FRAGMENTO)


@cache
def _indice_de_temas() -> Indice[EntradaDeTema]:
    return crear_indice(
        [
            ItemCompilado(patron, EntradaDeTema(peso=0, grupo=tema.tema, tema=tema))
            for tema in temas_de_norma()
            for plantilla in tema.plantillas
            for patron in compilar_plantilla(plantilla)
        ]
    )


@cache
def _prioridad_de_tema() -> dict[TemaNorma, int]:
    return {tema.tema: prioridad for prioridad, tema in enumerate(temas_de_norma())}


@cache
def _fragmentos() -> dict[str, FragmentoNorma]:
    return fragmentos_por_id()


def temas_que_coinciden(reglas: ResultadoCorrupcion) -> list[TemaCoincidente]:
    frases_por_tema: dict[TemaNorma, tuple[TemaDeNorma, list[str]]] = {}
    for senal in reglas.senales:
        if senal.tipo not in SENALES_QUE_PUEDEN_CITAR_UN_SUPUESTO:
            continue
        for coincidencia in buscar_coincidencias(tokenizar(senal.frase), _indice_de_temas()):
            tema = coincidencia.entrada.tema
            _, frases = frases_por_tema.setdefault(tema.tema, (tema, []))
            if senal.frase not in frases:
                frases.append(senal.frase)
    ordenados = sorted(frases_por_tema.values(), key=lambda registro: _prioridad_de_tema()[registro[0].tema])
    return [TemaCoincidente(tema, tuple(frases)) for tema, frases in ordenados]


class Citador:
    def __init__(self, fragmentos: Mapping[str, FragmentoNorma]) -> None:
        self._fragmentos = fragmentos
        self._ya_citados: set[str] = set()

    def agregar(
        self, destino: list[CitaDeNormaClasificada], fragmento_id: str, grupo: GrupoCita, senales: tuple[str, ...] = ()
    ) -> None:
        fragmento = self._fragmentos.get(fragmento_id)
        if fragmento is None or not fragmento.cita_automatica or fragmento_id in self._ya_citados:
            return
        self._ya_citados.add(fragmento_id)
        destino.append(CitaDeNormaClasificada(fragmento_id, fragmento.referencia, grupo, senales))


def _citar_supuestos(citador: Citador, reglas: ResultadoCorrupcion, supuestos: list[CitaDeNormaClasificada]) -> None:
    for coincidente in temas_que_coinciden(reglas):
        for fragmento_id in coincidente.tema.fragmentos:
            if len(supuestos) >= MAXIMO_SUPUESTOS_CITADOS:
                break
            citador.agregar(supuestos, fragmento_id, GrupoCita.SUPUESTO, coincidente.frases)


def _citar_procedimiento_de_corrupcion(
    citador: Citador, reglas: ResultadoCorrupcion, procedimiento: list[CitaDeNormaClasificada]
) -> None:
    for fragmento_id in FRAGMENTOS_DE_PROCEDIMIENTO_SI_HAY_CORRUPCION:
        citador.agregar(procedimiento, fragmento_id, GrupoCita.PROCEDIMIENTO)
    for faltante in reglas.faltantes:
        citador.agregar(procedimiento, REQUISITO_POR_FALTANTE[faltante], GrupoCita.PROCEDIMIENTO)


def construir_trazabilidad_normas(
    reglas: ResultadoCorrupcion,
    propuesta: CategoriaIncidencia,
    *,
    propuesta_corrupcion: bool,
    fragmentos: Mapping[str, FragmentoNorma] | None = None,
) -> TrazabilidadDeNormas:
    citador = Citador(fragmentos if fragmentos is not None else _fragmentos())
    supuestos: list[CitaDeNormaClasificada] = []
    procedimiento: list[CitaDeNormaClasificada] = []
    if propuesta_corrupcion:
        _citar_supuestos(citador, reglas, supuestos)
        _citar_procedimiento_de_corrupcion(citador, reglas, procedimiento)
    elif propuesta in (CategoriaIncidencia.QUEJA, CategoriaIncidencia.RECLAMO):
        citador.agregar(procedimiento, FRAGMENTO_DE_DERIVACION_DE_QUEJAS_Y_RECLAMOS, GrupoCita.PROCEDIMIENTO)
        if propuesta == CategoriaIncidencia.RECLAMO:
            citador.agregar(procedimiento, FRAGMENTO_DE_DEFINICION_DE_RECLAMO, GrupoCita.PROCEDIMIENTO)
    return TrazabilidadDeNormas(
        version=VERSION_DE_NORMAS,
        etiqueta=ETIQUETA_REFERENCIA_ORIENTATIVA,
        supuestos=tuple(supuestos),
        procedimiento=tuple(procedimiento),
        sin_supuesto_identificado=propuesta_corrupcion and not supuestos,
        transcripcion_anexo_c_cotejada=TRANSCRIPCION_ANEXO_C_COTEJADA,
    )
