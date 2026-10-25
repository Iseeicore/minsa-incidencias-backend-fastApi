from app.incidencias.adapters.http.schemas_de_derivacion import (
    ConteosDeDerivacionesResponse,
    DerivacionDetalleResponse,
    DerivacionResumenResponse,
    PaginaDeDerivacionesResponse,
)
from app.incidencias.application.armar_caso import detallar
from app.incidencias.application.armar_derivacion import resumir_derivacion
from app.incidencias.domain.derivaciones import ConteosDeDerivaciones, DerivacionDetalle
from app.incidencias.domain.plazo import PlazosConfigurados
from app.shared.pagination import Pagina
from tests.helpers.builders import un_caso_consultado, una_derivacion_consultada

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)


def _resumen() -> DerivacionResumenResponse:
    return DerivacionResumenResponse.desde_dominio(resumir_derivacion(una_derivacion_consultada()))


def test_el_resumen_se_serializa_con_los_nombres_del_contrato() -> None:
    cuerpo = _resumen().model_dump(by_alias=True, mode="json")

    assert cuerpo == {
        "id": "4821",
        "codigoCaso": "MINSA-2026-000001",
        "fechaDerivacion": "2026-10-24T09:30:15.123Z",
        "origen": {"codigo": "OTRANS", "nombre": "Oficina de Transparencia"},
        "destino": {"codigo": "EESS-0001", "nombre": "Centro de Salud Uno", "codigoRenipress": "1"},
        "derivadoPor": "Lucía Ramos",
        "descripcion": "Corresponde a un reclamo.",
        "categoria": "reclamo",
        "estado": "derivado",
        "motivoArchivo": None,
    }


def test_la_pagina_conserva_el_cursor_y_la_bandera() -> None:
    pagina = Pagina([resumir_derivacion(una_derivacion_consultada())], "cursor", hay_mas=True)

    cuerpo = PaginaDeDerivacionesResponse.desde_dominio(pagina).model_dump(by_alias=True, mode="json")

    assert (cuerpo["siguiente"], cuerpo["hayMas"], len(cuerpo["items"])) == ("cursor", True, 1)


def test_los_conteos_serializan_en_gestion_en_camel_case() -> None:
    cuerpo = ConteosDeDerivacionesResponse.desde_dominio(ConteosDeDerivaciones(5, 1, 2, 1, 1)).model_dump(
        by_alias=True, mode="json"
    )

    assert cuerpo == {"todos": 5, "pendientes": 1, "enGestion": 2, "resueltos": 1, "archivados": 1}


def test_el_detalle_une_el_envio_y_el_caso() -> None:
    caso = detallar(un_caso_consultado(), None, PLAZOS, [], [])
    detalle = DerivacionDetalle(resumir_derivacion(una_derivacion_consultada()), caso)

    cuerpo = DerivacionDetalleResponse.desde_dominio(detalle).model_dump(by_alias=True, mode="json")

    assert cuerpo["derivacion"]["id"] == "4821"
    assert cuerpo["caso"]["codigo"] == "MINSA-2026-000001"
    assert cuerpo["caso"]["acciones"] == []
