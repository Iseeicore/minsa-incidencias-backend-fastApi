from app.constants.incidencias import CATEGORIA_DESDE_API
from app.enums.categoria_api import CategoriaApi
from app.enums.categoria_filtro import CategoriaFiltro
from app.enums.estado_api import EstadoApi
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.incidencias.application.filtros import filtros_de, sin_estado_ni_motivo
from app.incidencias.domain.consultas import FiltrosCasos, FiltrosConsulta
from app.incidencias.domain.plazo import PlazosConfigurados

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)


def test_sin_filtros_no_se_traduce_nada() -> None:
    assert filtros_de(FiltrosConsulta(), PLAZOS) == FiltrosCasos()


def test_el_estado_y_la_categoria_de_la_api_se_traducen_a_los_de_la_base() -> None:
    filtros = filtros_de(
        FiltrosConsulta(estado=EstadoApi.EN_GESTION, categoria=CategoriaFiltro.DENUNCIA_CORRUPCION), PLAZOS
    )

    assert filtros.estado is EstadoIncidencia.EN_GESTION
    assert filtros.categoria is CATEGORIA_DESDE_API[CategoriaApi.DENUNCIA_CORRUPCION]
    assert filtros.sin_categoria is False


def test_sin_categoria_se_traduce_a_la_bandera_y_no_a_una_categoria() -> None:
    filtros = filtros_de(FiltrosConsulta(categoria=CategoriaFiltro.SIN_CATEGORIA), PLAZOS)

    assert (filtros.categoria, filtros.sin_categoria) == (None, True)


def test_los_demas_filtros_pasan_tal_cual() -> None:
    filtros = filtros_de(
        FiltrosConsulta(
            texto="goteras",
            establecimiento="1234",
            motivo_archivo=MotivoArchivo.NO_CORRESPONDE,
            desde="2026-01-01",
            hasta="2026-01-31",
        ),
        PLAZOS,
    )

    assert (filtros.texto, filtros.establecimiento) == ("goteras", "1234")
    assert filtros.motivo_archivo is MotivoArchivo.NO_CORRESPONDE
    assert (filtros.desde, filtros.hasta, filtros.aviso_horas) == ("2026-01-01", "2026-01-31", None)


def test_el_filtro_de_plazo_lleva_las_horas_de_aviso_configuradas() -> None:
    assert filtros_de(FiltrosConsulta(por_vencer=True), PLAZOS).aviso_horas == 48


def test_quitar_el_estado_y_el_motivo_deja_lo_demas() -> None:
    filtros = FiltrosCasos(estado=EstadoIncidencia.DERIVADO, motivo_archivo=MotivoArchivo.NO_CORRESPONDE, texto="x")

    assert sin_estado_ni_motivo(filtros) == FiltrosCasos(texto="x")
