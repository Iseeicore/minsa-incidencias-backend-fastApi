import math

import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_coincidencias import EstadoCoincidencias
from app.enums.origen_clasificacion import OrigenClasificacion
from app.enums.senal_sensible import SenalSensible
from app.filtro_corrupcion.domain.clasificar_por_coincidencias import aplicar_coincidencias, clasificar_por_reglas
from app.filtro_corrupcion.domain.tipos import ContextoEvaluacion
from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia, ResultadoClasificacion

CORRUPCION = "El director del hospital me pidio una coima de 100 soles para operarme y no me dio recibo"
QUEJA = "El personal fue grosero y prepotente conmigo en la ventanilla del hospital"
RECLAMO = "Me cobraron la consulta aunque tengo seguro integral"
OTRO = "Buenas tardes quisiera saber el horario de atencion del hospital"
MIXTA = "El personal fue grosero y ademas me cobraron la consulta del seguro"
ACOSO = "El jefe de mi area me acosa sexualmente y me amenaza con despedirme"


def _candidato(categoria: CategoriaIncidencia, similitud: float) -> CandidatoCoincidencia:
    return CandidatoCoincidencia(categoria, similitud)


def _con_antecedentes(texto: str, *candidatos: CandidatoCoincidencia) -> ResultadoClasificacion:
    return aplicar_coincidencias(clasificar_por_reglas(texto), candidatos)


def test_una_denuncia_de_corrupcion_se_decide_con_las_reglas_y_pide_revision_de_otrans() -> None:
    resultado = clasificar_por_reglas(CORRUPCION)

    assert (resultado.categoria, resultado.origen) == (
        CategoriaIncidencia.DENUNCIA_CORRUPCION,
        OrigenClasificacion.REGLAS,
    )
    assert (resultado.revision_otrans, resultado.requiere_revision_humana) == (True, True)
    assert resultado.coincidencias.estado == EstadoCoincidencias.NO_CONSULTADA


def test_la_categoria_sale_de_las_senales_de_queja_y_reclamo() -> None:
    queja = clasificar_por_reglas(QUEJA)
    reclamo = clasificar_por_reglas(RECLAMO)
    otro = clasificar_por_reglas(OTRO)

    assert (queja.categoria, queja.origen) == (CategoriaIncidencia.QUEJA, OrigenClasificacion.REGLAS)
    assert [senal.frase for senal in queja.senales_queja_reclamo] == ["grosero", "prepotente"]
    assert (reclamo.categoria, reclamo.revision_otrans) == (CategoriaIncidencia.RECLAMO, False)
    assert (otro.categoria, otro.origen) == (CategoriaIncidencia.OTRO, OrigenClasificacion.SIN_COINCIDENCIAS)
    assert (queja.requiere_revision_humana, otro.coincidencias.estado) == (True, EstadoCoincidencias.NO_CONSULTADA)


def test_el_contexto_del_establecimiento_llega_a_las_reglas() -> None:
    sin_contexto = clasificar_por_reglas(CORRUPCION)
    con_contexto = clasificar_por_reglas(CORRUPCION, ContextoEvaluacion(establecimiento_conocido=True))

    assert sin_contexto.reglas.faltantes != con_contexto.reglas.faltantes


def test_los_antecedentes_que_respaldan_la_categoria_de_las_reglas_quitan_la_revision_humana() -> None:
    resultado = _con_antecedentes(QUEJA, _candidato(CategoriaIncidencia.QUEJA, 0.9))

    assert resultado.origen == OrigenClasificacion.REGLAS_CON_APOYO_BD
    assert (resultado.categoria, resultado.requiere_revision_humana) == (CategoriaIncidencia.QUEJA, False)
    assert resultado.coincidencias.estado == EstadoCoincidencias.CORROBORADA
    assert resultado.coincidencias.margen == 0.9


def test_los_antecedentes_de_otra_categoria_sin_senal_en_el_relato_quedan_contradictorios() -> None:
    resultado = _con_antecedentes(QUEJA, _candidato(CategoriaIncidencia.RECLAMO, 0.9))

    assert (resultado.categoria, resultado.origen) == (CategoriaIncidencia.QUEJA, OrigenClasificacion.REGLAS)
    assert resultado.coincidencias.estado == EstadoCoincidencias.CONTRADICTORIA
    assert resultado.requiere_revision_humana is True


@pytest.mark.parametrize("categoria", [CategoriaIncidencia.OTRO, CategoriaIncidencia.DENUNCIA_CORRUPCION])
def test_los_antecedentes_nunca_llevan_un_relato_a_otro_o_a_corrupcion(categoria: CategoriaIncidencia) -> None:
    resultado = _con_antecedentes(OTRO, _candidato(categoria, 0.95))

    assert (resultado.categoria, resultado.coincidencias.estado) == (
        CategoriaIncidencia.OTRO,
        EstadoCoincidencias.CONTRADICTORIA,
    )


def test_en_un_relato_mixto_los_antecedentes_pueden_elegir_entre_queja_y_reclamo_y_pide_revision() -> None:
    resultado = _con_antecedentes(MIXTA, _candidato(CategoriaIncidencia.QUEJA, 0.9))

    assert clasificar_por_reglas(MIXTA).categoria == CategoriaIncidencia.RECLAMO
    assert (resultado.categoria, resultado.origen) == (
        CategoriaIncidencia.QUEJA,
        OrigenClasificacion.REGLAS_CON_APOYO_BD,
    )
    assert resultado.requiere_revision_humana is True


def test_con_una_senal_sensible_solo_se_respalda_la_categoria_que_ya_propusieron_las_reglas() -> None:
    base = clasificar_por_reglas(ACOSO)
    respaldada = _con_antecedentes(ACOSO, _candidato(base.categoria, 0.9))
    otra = _con_antecedentes(ACOSO, _candidato(CategoriaIncidencia.QUEJA, 0.9))

    assert base.reglas.senal_sensible == SenalSensible.ACOSO
    assert (respaldada.origen, respaldada.requiere_revision_humana) == (OrigenClasificacion.REGLAS_CON_APOYO_BD, True)
    assert otra.coincidencias.estado == EstadoCoincidencias.CONTRADICTORIA


def test_sin_candidatos_o_con_candidatos_invalidos_no_hay_antecedentes() -> None:
    vacios = _con_antecedentes(QUEJA)
    invalidos = _con_antecedentes(
        QUEJA,
        _candidato(CategoriaIncidencia.QUEJA, math.nan),
        _candidato(CategoriaIncidencia.QUEJA, math.inf),
        _candidato(CategoriaIncidencia.QUEJA, -0.1),
        _candidato(CategoriaIncidencia.QUEJA, 1.5),
    )

    for resultado in (vacios, invalidos):
        assert resultado.coincidencias.estado == EstadoCoincidencias.SIN_CANDIDATOS
        assert (resultado.coincidencias.mejor, resultado.coincidencias.margen) == (None, None)
        assert resultado.categoria == CategoriaIncidencia.QUEJA


@pytest.mark.parametrize(
    ("similitud", "segunda", "estado"),
    [
        (0.59, 0.0, EstadoCoincidencias.INSUFICIENTE),
        (0.6, 0.0, EstadoCoincidencias.CORROBORADA),
        (0.8, 0.75, EstadoCoincidencias.INSUFICIENTE),
        (0.8, 0.7, EstadoCoincidencias.CORROBORADA),
        (1.0, 0.9, EstadoCoincidencias.CORROBORADA),
        (0.0, 0.0, EstadoCoincidencias.INSUFICIENTE),
    ],
)
def test_los_umbrales_de_semejanza_y_de_margen_deciden_si_los_antecedentes_alcanzan(
    similitud: float, segunda: float, estado: EstadoCoincidencias
) -> None:
    resultado = _con_antecedentes(
        QUEJA, _candidato(CategoriaIncidencia.QUEJA, similitud), _candidato(CategoriaIncidencia.RECLAMO, segunda)
    )

    assert resultado.coincidencias.estado == estado


def test_de_cada_categoria_cuenta_el_mejor_candidato_y_el_margen_se_redondea_a_cuatro_decimales() -> None:
    resultado = _con_antecedentes(
        QUEJA,
        _candidato(CategoriaIncidencia.RECLAMO, 0.5),
        _candidato(CategoriaIncidencia.QUEJA, 0.7),
        _candidato(CategoriaIncidencia.QUEJA, 0.9),
        _candidato(CategoriaIncidencia.RECLAMO, 0.6),
    )

    assert resultado.coincidencias.mejor == _candidato(CategoriaIncidencia.QUEJA, 0.9)
    assert resultado.coincidencias.margen == 0.3


def test_ante_un_empate_de_semejanza_se_ordena_por_el_nombre_de_la_categoria() -> None:
    resultado = _con_antecedentes(
        QUEJA, _candidato(CategoriaIncidencia.RECLAMO, 0.9), _candidato(CategoriaIncidencia.QUEJA, 0.9)
    )

    assert resultado.coincidencias.mejor == _candidato(CategoriaIncidencia.QUEJA, 0.9)
    assert (resultado.coincidencias.margen, resultado.coincidencias.estado) == (0.0, EstadoCoincidencias.INSUFICIENTE)
