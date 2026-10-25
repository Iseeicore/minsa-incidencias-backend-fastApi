from app.incidencias.adapters.http.schemas_de_ipress import IpressListadaResponse, PaginaDeIpressResponse
from app.incidencias.domain.ipress import IpressListada
from app.shared.pagination import Pagina


def _ipress() -> IpressListada:
    return IpressListada(3, "EESS-0001", "Centro de Salud", "1", "I", "I-3")


def test_la_ipress_se_serializa_como_un_area_de_tipo_establecimiento() -> None:
    cuerpo = IpressListadaResponse.desde_dominio(_ipress()).model_dump(by_alias=True, mode="json")

    assert cuerpo == {
        "id": 3,
        "codigo": "EESS-0001",
        "nombre": "Centro de Salud",
        "tipoArea": "ESTABLECIMIENTO",
        "establecimiento": {"codigoRenipress": "1", "nivelAtencion": "I", "categoria": "I-3"},
    }


def test_la_pagina_conserva_el_cursor_y_la_bandera() -> None:
    pagina = PaginaDeIpressResponse.desde_dominio(Pagina([_ipress()], "cursor", hay_mas=True))

    cuerpo = pagina.model_dump(by_alias=True, mode="json")

    assert (cuerpo["siguiente"], cuerpo["hayMas"], len(cuerpo["items"])) == ("cursor", True, 1)
