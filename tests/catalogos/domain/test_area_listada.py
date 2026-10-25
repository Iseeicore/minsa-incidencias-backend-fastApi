from dataclasses import FrozenInstanceError

import pytest

from app.catalogos.domain.area_listada import AreaListada, ConsultaAreas, EstablecimientoDeArea, FiltrosDeAreas
from app.enums.tipo_area import TipoArea


def test_el_area_listada_es_inmutable() -> None:
    area = AreaListada(1, "OTRANS", "OTRANS", TipoArea.OTRANS, None)

    with pytest.raises(FrozenInstanceError):
        area.nombre = "otro"  # type: ignore[misc]


def test_el_establecimiento_lleva_sus_datos_de_renipress() -> None:
    assert EstablecimientoDeArea("1234", None, "II-1").categoria == "II-1"


def test_los_valores_por_defecto_no_filtran_ni_restringen() -> None:
    assert ConsultaAreas(limite=5) == ConsultaAreas(limite=5, despues_de=None, tipo=None, texto=None)
    assert FiltrosDeAreas() == FiltrosDeAreas(None, None, None, restringir_a_un_area=False)
