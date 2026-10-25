import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.grupo_cita import GrupoCita
from app.enums.informacion_faltante_ia import InformacionFaltanteIa
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.enums.tipo_contacto import TipoContacto
from app.enums.variante_ia import VarianteIa
from app.incidencias.application.leer_senales_guardadas import SenalesGuardadas, leer_senales_guardadas
from app.incidencias.domain.analisis import (
    CitaGuardada,
    DecisionGuardada,
    DestinoSiTitular,
    FichaDeDerivacion,
    ModeloGuardado,
    NormasGuardadas,
    SenalDeAnalisis,
)

COMPLETO: dict[str, object] = {
    "senales": [{"frase": "me pidió plata", "tipo": "FUERTE", "peso": 3}],
    "explicacion": "Hay un pedido de dinero.",
    "informacionFaltante": ["pruebas", "autor_o_cargo"],
    "fichaDerivacion": {
        "codigoEntidad": "sis",
        "contactosDisponibles": ["OCI", "PROCURADOR"],
        "destinoSiTitular": {"texto": "A la PCM", "entidadDestinoCodigo": None},
        "aplicaAlTitular": True,
    },
    "normas": {
        "version": "normas-v1",
        "etiqueta": "Referencia",
        "transcripcionAnexoCCotejada": True,
        "sinSupuestoIdentificado": False,
        "citas": [
            {
                "fragmentoId": "ANEXO_C-III-a",
                "referencia": "Anexo C",
                "grupo": "SUPUESTO",
                "senalesQueLaMotivan": ["me pidió plata"],
            }
        ],
    },
    "decision": {
        "motivo": "REGLAS",
        "propuestaDelAnalisis": "DENUNCIA_CORRUPCION",
        "escalarAOtrans": True,
        "requiereRevisionHumana": True,
        "pesoIa": 4,
    },
    "modelo": {"variante": "V2C", "degradado": True},
}


def test_lo_guardado_completo_se_lee_con_sus_tipos() -> None:
    guardado = leer_senales_guardadas(COMPLETO)

    assert guardado.senales == (SenalDeAnalisis("me pidió plata", "FUERTE", 3),)
    assert guardado.explicacion == "Hay un pedido de dinero."
    assert guardado.informacion_faltante == (InformacionFaltanteIa.PRUEBAS, InformacionFaltanteIa.AUTOR_O_CARGO)
    assert guardado.ficha_derivacion == FichaDeDerivacion(
        "sis", (TipoContacto.OCI, TipoContacto.PROCURADOR), DestinoSiTitular("A la PCM", None), aplica_al_titular=True
    )
    assert guardado.normas == NormasGuardadas(
        "normas-v1",
        transcripcion_anexo_c_cotejada=True,
        sin_supuesto_identificado=False,
        citas=(CitaGuardada("ANEXO_C-III-a", "Anexo C", GrupoCita.SUPUESTO, ("me pidió plata",)),),
    )
    assert guardado.decision == DecisionGuardada(
        MotivoDeEscritura.REGLAS,
        CategoriaIncidencia.DENUNCIA_CORRUPCION,
        escalar_a_otrans=True,
        requiere_revision_humana=True,
        peso_ia=4,
    )
    assert guardado.modelo == ModeloGuardado(VarianteIa.V2C, degradado=True)


@pytest.mark.parametrize("crudo", [None, [], "texto", 5, {}])
def test_lo_que_no_es_un_objeto_o_esta_vacio_deja_todo_en_su_valor_por_defecto(crudo: object) -> None:
    assert leer_senales_guardadas(crudo) == SenalesGuardadas()


@pytest.mark.parametrize(
    "senales",
    [
        "no es lista",
        [{"frase": "a", "tipo": "FUERTE"}],
        [{"frase": 1, "tipo": "FUERTE", "peso": 1}],
        [{"frase": "a", "tipo": None, "peso": 1}],
        [{"frase": "a", "tipo": "FUERTE", "peso": True}],
        [{"frase": "a", "tipo": "FUERTE", "peso": "3"}],
        ["texto"],
        [{"frase": "a", "tipo": "FUERTE", "peso": 1}, {"frase": "b"}],
    ],
)
def test_una_lista_de_senales_con_un_elemento_invalido_se_descarta_completa(senales: object) -> None:
    assert leer_senales_guardadas({"senales": senales}).senales == ()


def test_los_pesos_decimales_se_conservan() -> None:
    guardado = leer_senales_guardadas({"senales": [{"frase": "a", "tipo": "MEDIA", "peso": 1.5}]})

    assert guardado.senales[0].peso == 1.5


@pytest.mark.parametrize("explicacion", [5, ["a"], {"a": 1}, True])
def test_una_explicacion_que_no_es_texto_se_descarta(explicacion: object) -> None:
    assert leer_senales_guardadas({"explicacion": explicacion}).explicacion is None


@pytest.mark.parametrize("faltante", ["no_existe", ["pruebas", "no_existe"], ["pruebas", 5], "pruebas", {"a": 1}])
def test_una_informacion_faltante_con_un_valor_invalido_se_descarta_completa(faltante: object) -> None:
    assert leer_senales_guardadas({"informacionFaltante": faltante}).informacion_faltante == ()


@pytest.mark.parametrize(
    "ficha",
    [
        "texto",
        {"contactosDisponibles": []},
        {"codigoEntidad": "sis"},
        {"codigoEntidad": "sis", "contactosDisponibles": "OCI"},
        {"codigoEntidad": "sis", "contactosDisponibles": ["OCI", "otro"]},
        {"codigoEntidad": 5, "contactosDisponibles": []},
    ],
)
def test_una_ficha_de_derivacion_incompleta_se_descarta(ficha: object) -> None:
    assert leer_senales_guardadas({"fichaDerivacion": ficha}).ficha_derivacion is None


def test_una_ficha_sin_destino_ni_marca_de_titular_se_lee_con_valores_neutros() -> None:
    guardado = leer_senales_guardadas({"fichaDerivacion": {"codigoEntidad": "sis", "contactosDisponibles": []}})

    assert guardado.ficha_derivacion == FichaDeDerivacion("sis", (), None, aplica_al_titular=False)


@pytest.mark.parametrize("destino", ["texto", {"entidadDestinoCodigo": "x"}, {"texto": 5}])
def test_un_destino_si_titular_invalido_se_descarta_pero_la_ficha_se_conserva(destino: object) -> None:
    ficha = {"codigoEntidad": "sis", "contactosDisponibles": [], "destinoSiTitular": destino}

    guardado = leer_senales_guardadas({"fichaDerivacion": ficha})

    assert guardado.ficha_derivacion is not None
    assert guardado.ficha_derivacion.destino_si_titular is None


@pytest.mark.parametrize(
    "normas",
    ["texto", {}, {"version": 5}, {"version": "v1", "etiqueta": 5}, {"version": "v1", "etiqueta": None}, None],
)
def test_unas_normas_sin_version_de_texto_o_con_etiqueta_invalida_se_descartan(normas: object) -> None:
    assert leer_senales_guardadas({"normas": normas}).normas is None


def test_unas_normas_sin_etiqueta_son_validas_y_los_indicadores_invalidos_valen_falso() -> None:
    guardado = leer_senales_guardadas(
        {"normas": {"version": "v1", "transcripcionAnexoCCotejada": "si", "sinSupuestoIdentificado": 1}}
    )

    assert guardado.normas == NormasGuardadas(
        "v1", transcripcion_anexo_c_cotejada=False, sin_supuesto_identificado=False, citas=()
    )


@pytest.mark.parametrize(
    "citas",
    [
        "texto",
        [{"fragmentoId": "a", "referencia": "r", "grupo": "OTRO"}],
        [{"fragmentoId": "a", "referencia": "r"}],
        [{"fragmentoId": 5, "referencia": "r", "grupo": "SUPUESTO"}],
        [{"fragmentoId": "a", "grupo": "SUPUESTO"}],
        ["texto"],
        [{"fragmentoId": "a", "referencia": "r", "grupo": "SUPUESTO"}, {"fragmentoId": "b"}],
    ],
)
def test_una_lista_de_citas_con_un_elemento_invalido_se_descarta_completa(citas: object) -> None:
    guardado = leer_senales_guardadas({"normas": {"version": "v1", "citas": citas}})

    assert guardado.normas is not None
    assert guardado.normas.citas == ()


@pytest.mark.parametrize("motivadas", ["texto", ["a", 5], None])
def test_unas_senales_que_motivan_invalidas_quedan_vacias_sin_perder_la_cita(motivadas: object) -> None:
    cita = {"fragmentoId": "a", "referencia": "r", "grupo": "PROCEDIMIENTO", "senalesQueLaMotivan": motivadas}

    guardado = leer_senales_guardadas({"normas": {"version": "v1", "citas": [cita]}})

    assert guardado.normas is not None
    assert guardado.normas.citas == (CitaGuardada("a", "r", GrupoCita.PROCEDIMIENTO, ()),)


def test_una_decision_con_campos_invalidos_usa_los_valores_por_defecto_campo_a_campo() -> None:
    guardado = leer_senales_guardadas(
        {
            "decision": {
                "motivo": "no existe",
                "propuestaDelAnalisis": "OTRA",
                "escalarAOtrans": "si",
                "requiereRevisionHumana": None,
                "pesoIa": "4",
            }
        }
    )

    assert guardado.decision == DecisionGuardada(
        MotivoDeEscritura.SIN_CORRUPCION, None, escalar_a_otrans=False, requiere_revision_humana=False, peso_ia=None
    )


@pytest.mark.parametrize("decision", ["texto", 5, [], None])
def test_una_decision_que_no_es_un_objeto_se_descarta(decision: object) -> None:
    assert leer_senales_guardadas({"decision": decision}).decision is None


def test_un_modelo_invalido_se_lee_campo_a_campo_y_uno_que_no_es_objeto_se_descarta() -> None:
    parcial = leer_senales_guardadas({"modelo": {"variante": "V9", "degradado": "x"}})
    ajeno = leer_senales_guardadas({"modelo": "texto"})

    assert parcial.modelo == ModeloGuardado(None, degradado=False)
    assert ajeno.modelo is None
