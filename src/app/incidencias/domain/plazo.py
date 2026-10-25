from dataclasses import dataclass
from datetime import datetime, timedelta

from app.constants.incidencias import ESTADOS_ABIERTOS
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.plazo_estado import PlazoEstado
from app.enums.plazo_tipo import PlazoTipo
from app.incidencias.domain.tiempo import a_iso, horas_entre


@dataclass(frozen=True, slots=True)
class PlazosConfigurados:
    vigencia_dias: int
    aviso_horas: int


@dataclass(frozen=True, slots=True)
class PlazoCalculado:
    tipo: PlazoTipo | None
    estado: PlazoEstado | None
    vence_en: str | None
    horas_restantes: int | None


SIN_PLAZO = PlazoCalculado(None, None, None, None)


def _estado_de_atencion(vence_en: datetime, ahora: datetime, horas_restantes: int, aviso_horas: int) -> PlazoEstado:
    if vence_en <= ahora:
        return PlazoEstado.VENCIDO
    if horas_restantes <= aviso_horas:
        return PlazoEstado.POR_VENCER
    return PlazoEstado.EN_PLAZO


def _plazo_de_atencion(vence_en: datetime, ahora: datetime, aviso_horas: int) -> PlazoCalculado:
    horas_restantes = horas_entre(ahora, vence_en)
    estado = _estado_de_atencion(vence_en, ahora, horas_restantes, aviso_horas)
    return PlazoCalculado(PlazoTipo.ATENCION, estado, a_iso(vence_en), horas_restantes)


def calcular_plazo(
    estado: EstadoIncidencia,
    vence_atencion_en: datetime | None,
    resuelto_en: datetime | None,
    ahora: datetime,
    plazos: PlazosConfigurados,
) -> PlazoCalculado:
    if estado in ESTADOS_ABIERTOS:
        if vence_atencion_en is None:
            return SIN_PLAZO
        return _plazo_de_atencion(vence_atencion_en, ahora, plazos.aviso_horas)
    if estado == EstadoIncidencia.RESUELTO and resuelto_en is not None:
        vence_en = resuelto_en + timedelta(days=plazos.vigencia_dias)
        vigente = PlazoEstado.VENCIDO if vence_en <= ahora else PlazoEstado.EN_PLAZO
        return PlazoCalculado(PlazoTipo.VIGENCIA, vigente, a_iso(vence_en), horas_entre(ahora, vence_en))
    return SIN_PLAZO
