import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.enums.origen_propuesta import OrigenPropuesta
from app.filtro_corrupcion.domain.regla_de_escritura import construir_version_clasificador, decidir_escritura
from tests.helpers.corrupcion import un_analisis_clasificado, un_resultado_de_corrupcion


def test_una_propuesta_de_las_reglas_se_escribe_como_denuncia_con_la_confianza_topada_a_95() -> None:
    analisis = un_analisis_clasificado(
        reglas=un_resultado_de_corrupcion(propuesta_corrupcion=True, origen_propuesta=OrigenPropuesta.REGLAS),
        confianza=99.999,
    )

    decision = decidir_escritura(analisis)

    assert (decision.categoria, decision.motivo, decision.confianza) == (
        CategoriaIncidencia.DENUNCIA_CORRUPCION,
        MotivoDeEscritura.REGLAS,
        95,
    )


def test_una_propuesta_por_identidad_deja_ese_motivo() -> None:
    analisis = un_analisis_clasificado(
        reglas=un_resultado_de_corrupcion(propuesta_corrupcion=True, origen_propuesta=OrigenPropuesta.IDENTIDAD),
        confianza=51.666,
    )

    decision = decidir_escritura(analisis)

    assert (decision.motivo, decision.confianza) == (MotivoDeEscritura.IDENTIDAD, 51.67)


def test_la_duda_de_las_reglas_se_escribe_como_denuncia_con_la_confianza_topada_a_55() -> None:
    analisis = un_analisis_clasificado(
        reglas=un_resultado_de_corrupcion(requiere_segunda_opinion=True), revision_otrans=True, confianza=80
    )

    decision = decidir_escritura(analisis)

    assert (decision.categoria, decision.motivo, decision.confianza) == (
        CategoriaIncidencia.DENUNCIA_CORRUPCION,
        MotivoDeEscritura.DUDA_SIN_MODELO,
        55,
    )


@pytest.mark.parametrize(("confianza", "esperada"), [(87.456, 87.46), (-4, 0), (0.004, 0), (0.005, 0.01), (40, 40)])
def test_sin_corrupcion_se_escribe_la_categoria_propuesta_con_dos_decimales_entre_cero_y_95(
    confianza: float, esperada: float
) -> None:
    analisis = un_analisis_clasificado(categoria=CategoriaIncidencia.RECLAMO, confianza=confianza)

    decision = decidir_escritura(analisis)

    assert (decision.categoria, decision.motivo, decision.confianza) == (
        CategoriaIncidencia.RECLAMO,
        MotivoDeEscritura.SIN_CORRUPCION,
        esperada,
    )


def test_la_decision_conserva_la_propuesta_del_analisis_y_si_hay_que_escalar() -> None:
    reglas = un_resultado_de_corrupcion(escalar_a_otrans=True)
    analisis = un_analisis_clasificado(categoria=CategoriaIncidencia.QUEJA, reglas=reglas)

    decision = decidir_escritura(analisis)

    assert (decision.propuesta_del_analisis, decision.escalar_a_otrans) == (CategoriaIncidencia.QUEJA, True)


def test_la_version_une_la_de_las_reglas_con_la_del_motor() -> None:
    assert construir_version_clasificador("reglas-corrupcion-v1.3", "coincidencias-v1") == (
        "reglas-corrupcion-v1.3+coincidencias-v1"
    )
