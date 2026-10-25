from dataclasses import FrozenInstanceError

import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.filtro_corrupcion.domain.tipos import (
    ContextoEvaluacion,
    EntidadCatalogo,
    IdentidadDetectada,
    ResultadoQuejaReclamo,
    SenalQuejaReclamo,
)


def test_la_identidad_vacia_no_tiene_puntos_ni_hallazgos() -> None:
    identidad = IdentidadDetectada()

    assert (identidad.puntos, identidad.entidad, identidad.titular, identidad.ubicacion) == (0, None, None, None)
    assert (identidad.via_entidad, identidad.nombre_coincide) == (None, False)


def test_el_resultado_de_queja_y_reclamo_guarda_la_categoria_y_las_senales() -> None:
    senal = SenalQuejaReclamo("cobro", CategoriaIncidencia.RECLAMO)
    resultado = ResultadoQuejaReclamo(CategoriaIncidencia.RECLAMO, (senal,))

    assert (resultado.categoria, resultado.senales) == (CategoriaIncidencia.RECLAMO, (senal,))


def test_el_contexto_por_defecto_usa_el_catalogo_oficial_y_no_conoce_el_establecimiento() -> None:
    contexto = ContextoEvaluacion()

    assert (contexto.entidades, contexto.establecimiento_conocido, contexto.tiene_archivos) == (None, False, False)


def test_una_entidad_sin_datos_extra_queda_con_valores_vacios_y_no_se_modifica() -> None:
    entidad = EntidadCatalogo("x", "X")

    assert (entidad.alias, entidad.alias_derivados, entidad.contactos_disponibles) == ((), (), ())
    with pytest.raises(FrozenInstanceError):
        entidad.nombre = "Y"  # type: ignore[misc]
