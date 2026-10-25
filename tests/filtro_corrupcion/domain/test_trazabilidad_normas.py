from app.constants.normas import ETIQUETA_REFERENCIA_ORIENTATIVA, VERSION_DE_NORMAS
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.faltante_corrupcion import FaltanteCorrupcion
from app.enums.grupo_cita import GrupoCita
from app.enums.tema_norma import TemaNorma
from app.enums.tipo_senal import TipoSenal
from app.filtro_corrupcion.domain.evaluar_texto import evaluar_texto_corrupcion
from app.filtro_corrupcion.domain.tipos import SenalDetectada
from app.filtro_corrupcion.domain.trazabilidad_normas import (
    construir_trazabilidad_normas,
    temas_de_norma,
    temas_que_coinciden,
)
from app.shared.normas import FragmentoNorma
from tests.helpers.corrupcion import un_resultado_de_corrupcion

CORRUPCION = "El director del hospital me pidio una coima de 100 soles para operarme y no me dio recibo"


def _fragmento(identificador: str, *, cita_automatica: bool = True) -> FragmentoNorma:
    return FragmentoNorma(
        identificador, "FUENTE", f"ref {identificador}", "titulo", "FALTA", "texto", cita_automatica, None
    )


def _fragmentos(*identificadores: str, sin_cita: tuple[str, ...] = ()) -> dict[str, FragmentoNorma]:
    todos = {identificador: _fragmento(identificador) for identificador in identificadores}
    return {**todos, **{identificador: _fragmento(identificador, cita_automatica=False) for identificador in sin_cita}}


def _senal(frase: str, tipo: TipoSenal = TipoSenal.FUERTE) -> SenalDetectada:
    return SenalDetectada(frase, tipo, 3)


def test_hay_catorce_temas_y_el_primero_es_el_de_soborno_o_cobro() -> None:
    temas = temas_de_norma()

    assert len(temas) == 14
    assert (temas[0].tema, temas[0].fragmentos) == (TemaNorma.SOBORNO_O_COBRO, ("ANEXO_C-III-b",))


def test_solo_las_senales_de_corrupcion_proponen_temas_y_cada_frase_cuenta_una_vez_por_tema() -> None:
    reglas = un_resultado_de_corrupcion(
        senales=(_senal("coima"), _senal("soborno"), _senal("coima"), _senal("coima", TipoSenal.ACTOR))
    )

    coincidentes = temas_que_coinciden(reglas)

    assert [(c.tema.tema, c.frases) for c in coincidentes] == [(TemaNorma.SOBORNO_O_COBRO, ("coima", "soborno"))]


def test_los_temas_salen_en_el_orden_de_prioridad_del_mapa() -> None:
    reglas = un_resultado_de_corrupcion(senales=(_senal("influencias"), _senal("exige"), _senal("coima")))

    assert [c.tema.tema for c in temas_que_coinciden(reglas)] == [
        TemaNorma.SOBORNO_O_COBRO,
        TemaNorma.EXIGENCIA,
        TemaNorma.TRAFICO_DE_INFLUENCIAS,
    ]


def test_una_denuncia_cita_el_supuesto_que_motiva_las_senales_y_el_procedimiento_con_los_requisitos_que_faltan() -> (
    None
):
    reglas = evaluar_texto_corrupcion(CORRUPCION)

    trazabilidad = construir_trazabilidad_normas(
        reglas, CategoriaIncidencia.DENUNCIA_CORRUPCION, propuesta_corrupcion=True
    )

    assert (trazabilidad.version, trazabilidad.etiqueta) == (VERSION_DE_NORMAS, ETIQUETA_REFERENCIA_ORIENTATIVA)
    assert [(c.fragmento_id, c.grupo) for c in trazabilidad.supuestos] == [("ANEXO_C-III-b", GrupoCita.SUPUESTO)]
    assert trazabilidad.supuestos[0].senales_que_la_motivan == ("pidio una coima de monto para operarme", "coima")
    assert [c.fragmento_id for c in trazabilidad.procedimiento] == [
        "AM-DENUNCIA-CORRUPCION",
        "AM-CRITERIOS-DENUNCIA",
        "AM-DERIVA-STPAD-OCI-PP",
        "AM-REQ-ENTIDAD",
        "AM-REQ-PRUEBAS",
    ]
    assert (trazabilidad.sin_supuesto_identificado, trazabilidad.transcripcion_anexo_c_cotejada) == (False, False)


def test_los_supuestos_citados_no_pasan_de_tres() -> None:
    reglas = un_resultado_de_corrupcion(
        senales=(_senal("coima"), _senal("exige"), _senal("influencias"), _senal("abuso de poder"))
    )
    fragmentos = _fragmentos("ANEXO_C-III-b", "ANEXO_C-III-d", "ANEXO_C-III-i", "ANEXO_C-II-f", "ANEXO_C-I-e")

    trazabilidad = construir_trazabilidad_normas(
        reglas, CategoriaIncidencia.DENUNCIA_CORRUPCION, propuesta_corrupcion=True, fragmentos=fragmentos
    )

    assert [c.fragmento_id for c in trazabilidad.supuestos] == ["ANEXO_C-III-b", "ANEXO_C-III-d", "ANEXO_C-III-i"]


def test_un_fragmento_no_se_cita_dos_veces_ni_si_la_norma_no_permite_citarlo_automaticamente() -> None:
    reglas = un_resultado_de_corrupcion(
        senales=(_senal("se quedo con la plata"), _senal("se robaron"), _senal("coima"))
    )
    fragmentos = _fragmentos("ANEXO_C-III-h", "AM-DENUNCIA-CORRUPCION", sin_cita=("ANEXO_C-III-b", "ANEXO_C-I-b"))

    trazabilidad = construir_trazabilidad_normas(
        reglas, CategoriaIncidencia.DENUNCIA_CORRUPCION, propuesta_corrupcion=True, fragmentos=fragmentos
    )

    assert [c.fragmento_id for c in trazabilidad.supuestos] == ["ANEXO_C-III-h"]
    assert [c.fragmento_id for c in trazabilidad.procedimiento] == ["AM-DENUNCIA-CORRUPCION"]


def test_una_propuesta_de_corrupcion_sin_senales_que_calcen_queda_sin_supuesto_identificado() -> None:
    reglas = un_resultado_de_corrupcion(faltantes=(FaltanteCorrupcion.AUTOR_O_CARGO,))
    fragmentos = _fragmentos("AM-REQ-AUTORES")

    trazabilidad = construir_trazabilidad_normas(
        reglas, CategoriaIncidencia.DENUNCIA_CORRUPCION, propuesta_corrupcion=True, fragmentos=fragmentos
    )

    assert trazabilidad.supuestos == ()
    assert trazabilidad.sin_supuesto_identificado is True
    assert [c.fragmento_id for c in trazabilidad.procedimiento] == ["AM-REQ-AUTORES"]


def test_una_queja_cita_solo_la_derivacion_y_un_reclamo_cita_ademas_su_definicion() -> None:
    reglas = un_resultado_de_corrupcion()

    queja = construir_trazabilidad_normas(reglas, CategoriaIncidencia.QUEJA, propuesta_corrupcion=False)
    reclamo = construir_trazabilidad_normas(reglas, CategoriaIncidencia.RECLAMO, propuesta_corrupcion=False)

    assert [c.fragmento_id for c in queja.procedimiento] == ["AM-DERIVA-QUEJAS-RECLAMOS"]
    assert [c.fragmento_id for c in reclamo.procedimiento] == ["AM-DERIVA-QUEJAS-RECLAMOS", "AM-DEF-RECLAMO"]
    assert (queja.supuestos, queja.sin_supuesto_identificado) == ((), False)


def test_otro_no_cita_ninguna_norma() -> None:
    trazabilidad = construir_trazabilidad_normas(
        un_resultado_de_corrupcion(), CategoriaIncidencia.OTRO, propuesta_corrupcion=False
    )

    assert (trazabilidad.supuestos, trazabilidad.procedimiento) == ((), ())
