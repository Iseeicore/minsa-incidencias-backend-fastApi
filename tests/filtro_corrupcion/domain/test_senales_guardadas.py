from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.enums.tipo_senal import TipoSenal
from app.filtro_corrupcion.domain.regla_de_escritura import DecisionDeEscritura
from app.filtro_corrupcion.domain.senales_guardadas import construir_senales_guardadas
from app.filtro_corrupcion.domain.tipos import SenalDetectada
from tests.helpers.corrupcion import un_analisis_clasificado, un_resultado_de_corrupcion


def _decision(**cambios: object) -> DecisionDeEscritura:
    base = {
        "categoria": CategoriaIncidencia.QUEJA,
        "confianza": 51.67,
        "motivo": MotivoDeEscritura.SIN_CORRUPCION,
        "propuesta_del_analisis": CategoriaIncidencia.QUEJA,
        "escalar_a_otrans": False,
    }
    return DecisionDeEscritura(**{**base, **cambios})  # type: ignore[arg-type]


def test_las_senales_guardadas_llevan_las_senales_de_las_reglas_y_el_texto_de_la_explicacion() -> None:
    senal = SenalDetectada("coima", TipoSenal.FUERTE, 3)
    analisis = un_analisis_clasificado(reglas=un_resultado_de_corrupcion(senales=(senal,), puntaje=3))

    guardadas = construir_senales_guardadas(analisis, _decision())

    assert guardadas.senales == (senal,)
    assert guardadas.explicacion == analisis.explicacion
    assert (guardadas.clasificacion, guardadas.ficha_derivacion) == (analisis.clasificacion, None)
    assert guardadas.informacion_faltante == analisis.informacion_faltante


def test_las_citas_van_primero_los_supuestos_y_luego_el_procedimiento() -> None:
    analisis = un_analisis_clasificado(categoria=CategoriaIncidencia.RECLAMO)

    guardadas = construir_senales_guardadas(analisis, _decision())

    trazabilidad = analisis.trazabilidad_normas
    assert guardadas.normas.citas == (*trazabilidad.supuestos, *trazabilidad.procedimiento)
    assert [cita.fragmento_id for cita in guardadas.normas.citas] == ["AM-DERIVA-QUEJAS-RECLAMOS", "AM-DEF-RECLAMO"]
    assert (guardadas.normas.version, guardadas.normas.etiqueta) == (trazabilidad.version, trazabilidad.etiqueta)
    assert guardadas.normas.sin_supuesto_identificado is False


def test_la_decision_guardada_junta_lo_que_propuso_el_analisis_y_lo_que_se_escribio() -> None:
    analisis = un_analisis_clasificado(
        reglas=un_resultado_de_corrupcion(puntaje=2), revision_otrans=True, requiere_revision_humana=False, confianza=88
    )
    decision = _decision(
        categoria=CategoriaIncidencia.DENUNCIA_CORRUPCION,
        confianza=55,
        motivo=MotivoDeEscritura.DUDA_SIN_MODELO,
        escalar_a_otrans=True,
    )

    guardada = construir_senales_guardadas(analisis, decision).decision

    assert (guardada.categoria_escrita, guardada.motivo) == (
        CategoriaIncidencia.DENUNCIA_CORRUPCION,
        MotivoDeEscritura.DUDA_SIN_MODELO,
    )
    assert (guardada.propuesta_del_analisis, guardada.escalar_a_otrans) == (CategoriaIncidencia.QUEJA, True)
    assert (guardada.confianza_del_analisis, guardada.confianza_escrita) == (88, 55)
    assert (guardada.requiere_revision_humana, guardada.revision_otrans) == (False, True)
    assert (guardada.puntaje_reglas, guardada.puntaje_total) == (2, 2)
