from app.catalogos.adapters.http.areas_schemas import AreaListadaResponse, PaginaDeAreasResponse
from app.catalogos.domain.area_listada import AreaListada, EstablecimientoDeArea
from app.enums.tipo_area import TipoArea
from app.shared.pagination import Pagina


def test_un_area_con_establecimiento_lo_serializa_con_los_nombres_del_contrato() -> None:
    establecimiento = EstablecimientoDeArea("1234", "II-1", None)
    area = AreaListada(10, "HOSP-01", "Hospital Uno", TipoArea.ESTABLECIMIENTO, establecimiento)

    cuerpo = AreaListadaResponse.desde_dominio(area).model_dump(by_alias=True, mode="json")

    assert cuerpo == {
        "id": 10,
        "codigo": "HOSP-01",
        "nombre": "Hospital Uno",
        "tipoArea": "ESTABLECIMIENTO",
        "establecimiento": {"codigoRenipress": "1234", "nivelAtencion": "II-1", "categoria": None},
    }


def test_un_area_sin_establecimiento_lo_deja_nulo() -> None:
    area = AreaListada(1, "OTRANS", "OTRANS", TipoArea.OTRANS, None)

    assert AreaListadaResponse.desde_dominio(area).establecimiento is None


def test_la_pagina_conserva_el_cursor_y_la_bandera_de_mas() -> None:
    area = AreaListada(1, "OTRANS", "OTRANS", TipoArea.OTRANS, None)

    pagina = PaginaDeAreasResponse.desde_dominio(Pagina([area], "cursor", hay_mas=True))

    assert pagina.model_dump(by_alias=True)["hayMas"] is True
    assert pagina.siguiente == "cursor"
