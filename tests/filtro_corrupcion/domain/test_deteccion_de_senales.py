import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.nivel_cargo import NivelCargo
from app.enums.senal_sensible import SenalSensible
from app.enums.tipo_senal import TipoSenal
from app.filtro_corrupcion.domain.deteccion_de_senales import (
    detectar_acoso,
    detectar_actor,
    detectar_senales,
    es_jefatura,
    esta_negada_la_frase,
    hay_verbo_de_cobro,
)
from app.filtro_corrupcion.domain.normalizar_texto import marcar_montos, tokenizar
from app.filtro_corrupcion.domain.tipos import ActorDetectado, SenalDetectada, TitularDetectado


def _palabras(texto: str) -> list[str]:
    return marcar_montos(tokenizar(texto))


def _senales(texto: str) -> list[tuple[str, str]]:
    return [(senal.frase, senal.tipo.value) for senal in detectar_senales(_palabras(texto))]


def test_una_frase_fuerte_se_detecta_con_su_peso() -> None:
    assert detectar_senales(_palabras("me pidio plata para atenderme")) == [
        SenalDetectada("me pidio plata para", TipoSenal.FUERTE, 3)
    ]


def test_las_palabras_sueltas_que_enganan_no_son_una_senal() -> None:
    assert _senales("quiero hacer una denuncia por abuso en el cobro y el pago") == []


def test_negar_el_cobro_quita_la_senal_generalizada() -> None:
    assert _senales("nunca me cobraron nada por la cita en el hospital") == [("nunca me cobraron", "NEGATIVA_DECISIVA")]
    assert ("me cobraron aparte", "MEDIA") in _senales("me cobraron aparte por la atencion")
    assert _senales("no me cobraron aparte por la atencion").count(("me cobraron aparte", "MEDIA")) == 0


def test_una_negativa_decisiva_precedida_de_una_negacion_no_cuenta() -> None:
    assert _senales("no pague en caja pero tampoco me cobraron") != []
    assert ("pague en caja", "NEGATIVA_DECISIVA") in _senales("pague en caja la tarifa")
    assert ("pague en caja", "NEGATIVA_DECISIVA") not in _senales("no pague en caja la tarifa")


def test_de_cada_tipo_de_negativa_solo_se_cuenta_la_primera() -> None:
    senales = _senales("pague en caja y me dieron la boleta con recibo en el hospital")

    assert [tipo for _, tipo in senales].count("NEGATIVA_DECISIVA") == 1


def test_los_montos_se_saltan_entre_las_palabras_de_una_frase() -> None:
    assert ("me pidio monto plata para", "FUERTE") in _senales("me pidio 100 soles plata para atenderme")


@pytest.mark.parametrize(
    ("palabras", "inicio", "fin", "esperado"),
    [
        (["no", "me", "cobraron"], 1, 3, True),
        (["nunca", "x", "me", "cobraron"], 2, 4, True),
        (["nunca", "x", "y", "me", "cobraron"], 3, 5, False),
        (["me", "cobraron", "ningun", "sol"], 0, 3, True),
        (["me", "cobraron", "un", "sol"], 0, 3, False),
        (["hola"], 0, 1, False),
    ],
)
def test_una_frase_esta_negada_si_los_dos_anteriores_o_la_propia_frase_traen_un_negador(
    palabras: list[str],
    inicio: int,
    fin: int,
    esperado: bool,  # noqa: FBT001
) -> None:
    assert esta_negada_la_frase(inicio, fin, palabras) is esperado


def test_el_actor_de_mayor_nivel_gana_sobre_los_de_linea_y_el_personal() -> None:
    resultado = detectar_actor(_palabras("el medico y la jefa de admision y el director general del hospital"))

    assert resultado is not None
    actor, senal = resultado
    assert actor == ActorDetectado("director general", NivelCargo.CARGO_MAXIMO)
    assert senal == SenalDetectada("director general", TipoSenal.ACTOR, 1)


def test_sin_cargos_no_hay_actor() -> None:
    assert detectar_actor(_palabras("el vecino del segundo piso")) is None


def test_a_igual_nivel_gana_el_primero_que_aparece() -> None:
    resultado = detectar_actor(_palabras("el medico y despues el enfermero"))

    assert resultado is not None
    assert resultado[0].cargo == "medico"


def test_las_palabras_de_jefatura_se_reconocen() -> None:
    assert es_jefatura(["la", "jefa", "llego"]) is True
    assert es_jefatura(["el", "vecino"]) is False


def test_un_verbo_de_cobro_solo_cuenta_si_no_esta_negado() -> None:
    assert hay_verbo_de_cobro(["me", "pidio", "algo"]) is True
    assert hay_verbo_de_cobro(["cobro", "algo"]) is True
    assert hay_verbo_de_cobro(["nunca", "pidio", "algo"]) is False
    assert hay_verbo_de_cobro(["la", "atencion", "fue", "buena"]) is False


def test_el_acoso_sensible_propone_reclamo_y_escala_solo_si_hay_cargo_mayor() -> None:
    palabras = _palabras("el jefe me acosa todos los dias")

    acoso = detectar_acoso(palabras, None, None)

    assert (acoso.senal_sensible, acoso.categoria_sugerida, acoso.escalar_a_otrans) == (
        SenalSensible.ACOSO,
        CategoriaIncidencia.RECLAMO,
        True,
    )


def test_el_acoso_de_un_cargo_menor_no_escala_a_otrans() -> None:
    acoso = detectar_acoso(
        _palabras("el enfermero me acosa en el turno"), ActorDetectado("enfermero", NivelCargo.PERSONAL), None
    )

    assert (acoso.senal_sensible, acoso.escalar_a_otrans) == (SenalSensible.ACOSO, False)


def test_el_titular_o_el_cargo_maximo_escalan_el_acoso() -> None:
    titular = TitularDetectado("director general", es_equivalente_del_maximo=False, nombre_coincide=False)
    maximo = ActorDetectado("director general", NivelCargo.CARGO_MAXIMO)

    assert detectar_acoso(_palabras("alguien me acosa"), None, titular).escalar_a_otrans is True
    assert detectar_acoso(_palabras("alguien me acosa"), maximo, None).escalar_a_otrans is True


def test_un_acoso_negado_o_ausente_no_se_detecta() -> None:
    assert detectar_acoso(_palabras("nunca me acosaron en el hospital"), None, None).senal_sensible is None
    assert detectar_acoso(_palabras("la atencion fue buena"), None, None).categoria_sugerida is None
