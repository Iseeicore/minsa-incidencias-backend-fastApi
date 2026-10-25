from app.constants.clasificacion import VERSION_CLASIFICADOR_ALGORITMICO
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.certeza_corrupcion import CertezaCorrupcion
from app.enums.estado_coincidencias import EstadoCoincidencias
from app.enums.faltante_corrupcion import FaltanteCorrupcion
from app.enums.informacion_faltante_ia import InformacionFaltanteIa
from app.enums.origen_clasificacion import OrigenClasificacion
from app.filtro_corrupcion.domain.adaptar_clasificacion import adaptar_clasificacion
from app.filtro_corrupcion.domain.tipos import ReferenciaDerivacion, SenalQuejaReclamo
from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia, ResumenCoincidencias
from tests.helpers.corrupcion import un_resultado_de_clasificacion, un_resultado_de_corrupcion


def test_la_explicacion_nombra_la_categoria_el_puntaje_el_apoyo_y_si_hace_falta_revision() -> None:
    resultado = un_resultado_de_clasificacion(
        categoria=CategoriaIncidencia.QUEJA,
        reglas=un_resultado_de_corrupcion(puntaje=2),
        requiere_revision_humana=False,
        coincidencias=ResumenCoincidencias(
            EstadoCoincidencias.CORROBORADA, CandidatoCoincidencia(CategoriaIncidencia.QUEJA, 0.9), 0.9
        ),
    )

    assert adaptar_clasificacion(resultado).explicacion == (
        "Categoría propuesta: Queja. Puntaje de reglas de corrupción: 2. "
        "Los antecedentes humanos respaldan la categoría con evidencia en el relato actual. "
        "La categoría puede confirmarse o corregirse."
    )


def test_la_explicacion_de_una_denuncia_pide_revision_humana() -> None:
    resultado = un_resultado_de_clasificacion(
        categoria=CategoriaIncidencia.DENUNCIA_CORRUPCION,
        coincidencias=ResumenCoincidencias(EstadoCoincidencias.NO_CONSULTADA, None, None),
    )

    assert adaptar_clasificacion(resultado).explicacion == (
        "Categoría propuesta: Denuncia por corrupción. Puntaje de reglas de corrupción: 0. "
        "No se utilizaron antecedentes para decidir la categoría. Se requiere revisión humana."
    )


def test_cada_faltante_de_las_reglas_se_traduce_a_la_informacion_que_se_le_pide_al_ciudadano() -> None:
    faltantes = (
        FaltanteCorrupcion.DATOS_INSUFICIENTES,
        FaltanteCorrupcion.AUTOR_O_CARGO,
        FaltanteCorrupcion.ENTIDAD,
        FaltanteCorrupcion.PRUEBAS,
    )

    analisis = adaptar_clasificacion(
        un_resultado_de_clasificacion(reglas=un_resultado_de_corrupcion(faltantes=faltantes))
    )

    assert analisis.informacion_faltante == (
        InformacionFaltanteIa.HECHO_DETALLADO,
        InformacionFaltanteIa.AUTOR_O_CARGO,
        InformacionFaltanteIa.ENTIDAD_O_UNIDAD,
        InformacionFaltanteIa.PRUEBAS,
    )


def test_las_banderas_de_otrans_vienen_de_las_reglas_y_de_la_clasificacion() -> None:
    ficha = ReferenciaDerivacion("minsa", (), None, aplica_al_titular=False)
    reglas = un_resultado_de_corrupcion(
        propuesta_corrupcion=True,
        escalar_a_otrans=True,
        referencia_derivacion=ficha,
        certeza=CertezaCorrupcion.ALTA,
        puntaje=6,
    )

    analisis = adaptar_clasificacion(
        un_resultado_de_clasificacion(
            reglas=reglas,
            revision_otrans=True,
            requiere_revision_humana=False,
            categoria=CategoriaIncidencia.DENUNCIA_CORRUPCION,
        )
    )

    assert (analisis.requiere_otrans, analisis.revision_otrans, analisis.escalar_a_otrans) == (True, True, True)
    assert (analisis.requiere_revision_humana, analisis.ficha_derivacion) == (False, ficha)
    assert (analisis.propuesta, analisis.reglas) == (CategoriaIncidencia.DENUNCIA_CORRUPCION, reglas)


def test_la_confianza_es_la_de_las_reglas_sin_modelo() -> None:
    analisis = adaptar_clasificacion(un_resultado_de_clasificacion())

    assert analisis.confianza == analisis.combinacion.confianza == 51.67
    assert analisis.combinacion.peso_ia is None


def test_el_detalle_de_clasificacion_conserva_version_origen_coincidencias_y_senales() -> None:
    senal = SenalQuejaReclamo("grosero", CategoriaIncidencia.QUEJA)
    coincidencias = ResumenCoincidencias(EstadoCoincidencias.SIN_CANDIDATOS, None, None)

    detalle = adaptar_clasificacion(
        un_resultado_de_clasificacion(
            origen=OrigenClasificacion.REGLAS, coincidencias=coincidencias, senales_queja_reclamo=(senal,)
        )
    ).clasificacion

    assert (detalle.version, detalle.origen) == (VERSION_CLASIFICADOR_ALGORITMICO, OrigenClasificacion.REGLAS)
    assert (detalle.coincidencias, detalle.senales_queja_reclamo) == (coincidencias, (senal,))
