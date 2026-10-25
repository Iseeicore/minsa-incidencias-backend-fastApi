from dataclasses import FrozenInstanceError

import pytest

from app.enums.alcance_indicadores import AlcanceIndicadores
from app.enums.tipo_area import TipoArea
from app.incidencias.domain.consultas import VisibilidadDeDerivaciones
from app.incidencias.domain.indicadores import (
    AlcanceDeIndicadores,
    AreaDeAlcance,
    ConsultaDeIndicadores,
    TarjetaDeIndicador,
)


def test_el_alcance_de_un_area_lleva_su_codigo_nombre_y_tipo() -> None:
    area = AreaDeAlcance("EESS-0001", "Centro de Salud", TipoArea.ESTABLECIMIENTO)

    alcance = AlcanceDeIndicadores(AlcanceIndicadores.AREA, area)

    assert (alcance.tipo, alcance.area) == (AlcanceIndicadores.AREA, area)


def test_la_consulta_une_la_visibilidad_con_el_alcance() -> None:
    alcance = AlcanceDeIndicadores(AlcanceIndicadores.TODO, None)

    consulta = ConsultaDeIndicadores(VisibilidadDeDerivaciones(), alcance)

    assert consulta.alcance is alcance


def test_las_tarjetas_no_se_modifican() -> None:
    tarjeta = TarjetaDeIndicador("recibidos", 1, None)  # type: ignore[arg-type]

    with pytest.raises(FrozenInstanceError):
        tarjeta.valor = 2  # type: ignore[misc]
