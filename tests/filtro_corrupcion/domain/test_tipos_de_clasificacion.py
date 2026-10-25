from dataclasses import FrozenInstanceError

import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_coincidencias import EstadoCoincidencias
from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia, ResumenCoincidencias


def test_el_resumen_guarda_el_estado_el_mejor_candidato_y_el_margen() -> None:
    mejor = CandidatoCoincidencia(CategoriaIncidencia.QUEJA, 0.8)

    resumen = ResumenCoincidencias(EstadoCoincidencias.CORROBORADA, mejor, 0.3)

    assert (resumen.estado, resumen.mejor, resumen.margen) == (EstadoCoincidencias.CORROBORADA, mejor, 0.3)


def test_un_candidato_no_se_modifica() -> None:
    candidato = CandidatoCoincidencia(CategoriaIncidencia.RECLAMO, 0.5)

    with pytest.raises(FrozenInstanceError):
        candidato.similitud = 0.9  # type: ignore[misc]
