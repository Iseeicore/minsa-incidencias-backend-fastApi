from app.enums.estado_incidencia import EstadoIncidencia
from app.incidencias.adapters.http.schemas import (
    CasoDetalleResponse,
    CasoResumenResponse,
    CasosPorVencerResponse,
    ConteosDeCasosResponse,
    PaginaDeCasosResponse,
)
from app.incidencias.application.armar_caso import detallar, resumir
from app.incidencias.application.contar_incidencias import ContarIncidencias
from app.incidencias.domain.casos import CasosPorVencer
from app.incidencias.domain.consultas import FiltrosConsulta
from app.incidencias.domain.plazo import PlazosConfigurados
from app.shared.pagination import Pagina
from tests.helpers.builders import un_caso_consultado, una_evidencia, una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
GESTOR = una_sesion(roles=("GESTOR",))


def _resumen() -> CasoResumenResponse:
    return CasoResumenResponse.desde_dominio(resumir(un_caso_consultado(), GESTOR, PLAZOS))


def test_el_resumen_se_serializa_con_los_nombres_y_los_nulos_fijos_del_contrato() -> None:
    cuerpo = _resumen().model_dump(by_alias=True, mode="json")

    assert cuerpo["codigo"] == "MINSA-2026-000001"
    assert (cuerpo["etiquetas"], cuerpo["prioridad"], cuerpo["organismo"]) == ([], None, None)
    assert cuerpo["categoriaIa"] == "reclamo"
    assert cuerpo["plazo"] == {
        "tipo": "atencion",
        "estado": "en-plazo",
        "venceEn": "2026-11-23T12:00:00.000Z",
        "horasRestantes": 720,
    }
    assert cuerpo["acciones"] == ["confirmar", "corregir", "archivar"]
    assert cuerpo["establecimiento"] == {
        "codigoRenipress": "1234",
        "nombre": "Hospital Uno",
        "nivelAtencion": "II",
        "categoria": "II-1",
    }


def test_el_detalle_hereda_el_resumen_y_agrega_sus_campos() -> None:
    caso = detallar(un_caso_consultado(), GESTOR, PLAZOS, [una_evidencia()], [])

    cuerpo = CasoDetalleResponse.desde_dominio(caso).model_dump(by_alias=True, mode="json")

    assert cuerpo["codigo"] == "MINSA-2026-000001"
    assert (cuerpo["resolucion"], cuerpo["archivo"], cuerpo["reapertura"]) == (None, None, None)
    assert cuerpo["evidencias"][0]["contenidoDisponible"] is True
    assert cuerpo["reclamante"] == "Anónimo"
    assert cuerpo["historial"] == []


def test_la_pagina_conserva_el_cursor_y_la_bandera() -> None:
    pagina = Pagina([resumir(un_caso_consultado(), GESTOR, PLAZOS)], "cursor", hay_mas=True)

    cuerpo = PaginaDeCasosResponse.desde_dominio(pagina).model_dump(by_alias=True, mode="json")

    assert (cuerpo["siguiente"], cuerpo["hayMas"], len(cuerpo["items"])) == ("cursor", True, 1)


async def test_los_conteos_serializan_el_estado_en_gestion_con_guion() -> None:
    lector = IncidenciasEnMemoria()
    lector.por_estado = {EstadoIncidencia.EN_GESTION: 2}
    conteos = await ContarIncidencias(lector, PLAZOS).execute(GESTOR, FiltrosConsulta())

    cuerpo = ConteosDeCasosResponse.desde_dominio(conteos).model_dump(by_alias=True, mode="json")

    assert cuerpo["porEstado"]["en-gestion"] == {"cantidad": 2, "conMas": False}
    assert set(cuerpo["porEstado"]) == {"registrado", "clasificado", "derivado", "en-gestion", "resuelto", "archivado"}
    assert cuerpo["todos"] == {"cantidad": 2, "conMas": False}


def test_el_resumen_de_la_campana_lista_sus_casos() -> None:
    resumen = CasosPorVencer(total=3, por_vencer=2, vencidos=1, casos=(resumir(un_caso_consultado(), GESTOR, PLAZOS),))

    cuerpo = CasosPorVencerResponse.desde_dominio(resumen).model_dump(by_alias=True, mode="json")

    assert (cuerpo["total"], cuerpo["porVencer"], cuerpo["vencidos"], len(cuerpo["casos"])) == (3, 2, 1, 1)
