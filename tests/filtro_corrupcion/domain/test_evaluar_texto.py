from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.certeza_corrupcion import CertezaCorrupcion
from app.enums.faltante_corrupcion import FaltanteCorrupcion
from app.enums.origen_propuesta import OrigenPropuesta
from app.enums.senal_sensible import SenalSensible
from app.enums.tipo_senal import TipoSenal
from app.enums.via_entidad import ViaEntidad
from app.filtro_corrupcion.domain.evaluar_texto import (
    aporte_de_identidad,
    evaluar_texto_corrupcion,
    puntos_de_identidad,
)
from app.filtro_corrupcion.domain.tipos import ContextoEvaluacion, EntidadCatalogo, SenalDetectada

SIN_ENTIDADES = ContextoEvaluacion(entidades=())


def _tipos(texto: str, contexto: ContextoEvaluacion | None = None) -> list[tuple[str, TipoSenal]]:
    return [(senal.frase, senal.tipo) for senal in evaluar_texto_corrupcion(texto, contexto).senales]


def test_un_texto_de_menos_de_20_caracteres_no_aplica_y_dice_que_faltan_datos() -> None:
    resultado = evaluar_texto_corrupcion("  corto  ")

    assert (resultado.aplica, resultado.puntaje, resultado.certeza) == (False, 0, CertezaCorrupcion.BAJA)
    assert resultado.faltantes == (FaltanteCorrupcion.DATOS_INSUFICIENTES,)
    assert (resultado.senales, resultado.entidad, resultado.referencia_derivacion) == ((), None, None)
    assert resultado.version_reglas == "reglas-corrupcion-v1.3"


def test_el_largo_se_mide_en_unidades_utf16_despues_de_recortar_como_javascript() -> None:
    assert evaluar_texto_corrupcion("😀" * 9 + "a").aplica is False
    assert evaluar_texto_corrupcion("😀" * 9 + "ab").aplica is True
    assert evaluar_texto_corrupcion("\ufeff\u00a0" + "x" * 19 + "\u00a0\ufeff").aplica is False


def test_una_frase_fuerte_con_cargo_y_entidad_propone_por_reglas_con_certeza_alta() -> None:
    resultado = evaluar_texto_corrupcion("La jefa del SIS me pidio plata para atenderme")

    assert (resultado.puntaje, resultado.certeza, resultado.origen_propuesta) == (
        5,
        CertezaCorrupcion.ALTA,
        OrigenPropuesta.REGLAS,
    )
    assert resultado.propuesta_corrupcion is True
    assert [(s.frase, s.tipo) for s in resultado.senales] == [
        ("me pidio plata para", TipoSenal.FUERTE),
        ("jefa del sis", TipoSenal.ACTOR),
        ("sis", TipoSenal.ENTIDAD),
    ]
    assert resultado.entidad is not None
    assert resultado.entidad.codigo == "sis"
    assert resultado.identidad.via_entidad == ViaEntidad.NOMBRE_O_ALIAS
    assert resultado.faltantes == (FaltanteCorrupcion.PRUEBAS,)
    assert resultado.requiere_otrans is True
    assert resultado.referencia_derivacion is not None
    assert resultado.referencia_derivacion.aplica_al_titular is True


def test_los_archivos_y_el_establecimiento_conocidos_quitan_faltantes() -> None:
    contexto = ContextoEvaluacion(entidades=(), tiene_archivos=True, establecimiento_conocido=True)

    resultado = evaluar_texto_corrupcion("Carlos Perez me pidio 100 soles para atenderme en el hospital", contexto)

    assert resultado.faltantes == ()
    sin_contexto = evaluar_texto_corrupcion(
        "Carlos Perez me pidio 100 soles para atenderme en el hospital", SIN_ENTIDADES
    )
    assert sin_contexto.faltantes == (FaltanteCorrupcion.ENTIDAD, FaltanteCorrupcion.PRUEBAS)


def test_decir_que_se_tienen_pruebas_quita_el_faltante_de_pruebas() -> None:
    resultado = evaluar_texto_corrupcion("La jefa del SIS me pidio plata para atenderme, tengo fotos del hecho")

    assert FaltanteCorrupcion.PRUEBAS not in resultado.faltantes


def test_sin_cargo_ni_nombre_ni_entidad_faltan_autor_y_entidad() -> None:
    resultado = evaluar_texto_corrupcion("me pidieron dinero para atenderme en emergencia ayer", SIN_ENTIDADES)

    assert resultado.faltantes == (
        FaltanteCorrupcion.AUTOR_O_CARGO,
        FaltanteCorrupcion.ENTIDAD,
        FaltanteCorrupcion.PRUEBAS,
    )


def test_un_texto_sin_indicios_no_propone_y_no_trae_faltantes() -> None:
    resultado = evaluar_texto_corrupcion("El vecino paso por la calle y no dijo nada importante hoy")

    assert (resultado.puntaje, resultado.propuesta_corrupcion, resultado.faltantes) == (0, False, ())
    assert (resultado.certeza, resultado.origen_propuesta, resultado.requiere_otrans) == (
        CertezaCorrupcion.BAJA,
        None,
        False,
    )


def test_una_negativa_decisiva_resta_y_evita_proponer() -> None:
    resultado = evaluar_texto_corrupcion("Nunca me cobraron nada por la cita, pague en caja con boleta oficial")

    assert resultado.puntaje == -2
    assert resultado.propuesta_corrupcion is False


def test_sin_frases_fuertes_pero_con_cargo_entidad_y_verbo_de_cobro_propone_por_identidad() -> None:
    resultado = evaluar_texto_corrupcion("La directora general del Seguro Integral de Salud cobra a los pacientes")

    assert (resultado.origen_propuesta, resultado.certeza, resultado.puntaje) == (
        OrigenPropuesta.IDENTIDAD,
        CertezaCorrupcion.BAJA,
        2,
    )
    assert resultado.requiere_segunda_opinion is True
    assert resultado.identidad.puntos == 2


def test_una_negativa_decisiva_impide_proponer_por_identidad() -> None:
    resultado = evaluar_texto_corrupcion(
        "La directora general del Seguro Integral de Salud cobra a los pacientes con tarifa oficial publicada"
    )

    assert resultado.origen_propuesta is None
    assert resultado.propuesta_corrupcion is False


def test_el_nombre_propio_mencionado_evita_el_faltante_de_autor() -> None:
    resultado = evaluar_texto_corrupcion("Carlos Perez me pidio 100 soles para atenderme en el hospital", SIN_ENTIDADES)

    assert resultado.nombre_mencionado == "Carlos Perez"
    assert FaltanteCorrupcion.AUTOR_O_CARGO not in resultado.faltantes


def test_el_acoso_de_un_cargo_mayor_sugiere_reclamo_y_escala_a_otrans_sin_proponer_corrupcion() -> None:
    resultado = evaluar_texto_corrupcion(
        "El jefe de admision acosa a las pacientes y me toco la pierna ayer", SIN_ENTIDADES
    )

    assert (resultado.senal_sensible, resultado.categoria_sugerida) == (
        SenalSensible.ACOSO,
        CategoriaIncidencia.RECLAMO,
    )
    assert (resultado.escalar_a_otrans, resultado.propuesta_corrupcion) == (True, False)


def test_con_entidades_propias_solo_se_detectan_esas_entidades() -> None:
    propias = ContextoEvaluacion(entidades=(EntidadCatalogo("zzz", "Clinica Zeta", alias=("Zeta",)),))

    resultado = evaluar_texto_corrupcion("Me pidieron plata para atenderme en la Clinica Zeta ayer", propias)
    por_defecto = evaluar_texto_corrupcion(
        "Me pidieron plata para atenderme en el Seguro Integral de Salud ayer", propias
    )

    assert resultado.entidad is not None
    assert resultado.entidad.codigo == "zzz"
    assert resultado.referencia_derivacion is not None
    assert resultado.referencia_derivacion.contactos_disponibles == ()
    assert por_defecto.entidad is None


def test_la_ubicacion_solo_aporta_si_no_hay_entidad_y_el_establecimiento_no_es_conocido() -> None:
    texto = "Me pidieron plata para atenderme en Huaycan ayer"

    con_zona = evaluar_texto_corrupcion(texto)
    conocido = evaluar_texto_corrupcion(texto, ContextoEvaluacion(establecimiento_conocido=True))

    assert (con_zona.identidad.ubicacion is not None, con_zona.identidad.puntos) == (True, 1)
    assert conocido.identidad.ubicacion is not None


def test_el_aporte_de_identidad_se_topa_en_cuatro_puntos() -> None:
    senales = [
        SenalDetectada("a", TipoSenal.ACTOR, 1),
        SenalDetectada("b", TipoSenal.ENTIDAD, 1),
        SenalDetectada("c", TipoSenal.NOMBRE_TITULAR, 2),
        SenalDetectada("d", TipoSenal.UBICACION, 1),
        SenalDetectada("e", TipoSenal.FUERTE, 3),
    ]

    assert aporte_de_identidad(senales) == 4
    assert aporte_de_identidad(senales[:2]) == 2
    assert aporte_de_identidad([]) == 0


def test_los_puntos_de_identidad_suman_cada_elemento_y_se_topan_en_cuatro() -> None:
    assert (
        puntos_de_identidad(hay_entidad_nombrada=True, hay_cargo=True, nombre_coincide=False, hay_ubicacion=False) == 2
    )
    assert (
        puntos_de_identidad(hay_entidad_nombrada=False, hay_cargo=False, nombre_coincide=True, hay_ubicacion=True) == 3
    )
    assert puntos_de_identidad(hay_entidad_nombrada=True, hay_cargo=True, nombre_coincide=True, hay_ubicacion=True) == 4
    assert (
        puntos_de_identidad(hay_entidad_nombrada=False, hay_cargo=False, nombre_coincide=False, hay_ubicacion=False)
        == 0
    )


def test_un_texto_solo_con_montos_los_ignora() -> None:
    assert _tipos("pago 100 soles por la cita de mi hijo en el hospital central", SIN_ENTIDADES) == []
