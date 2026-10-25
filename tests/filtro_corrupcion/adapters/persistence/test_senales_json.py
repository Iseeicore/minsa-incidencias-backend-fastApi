import json
from typing import Any

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_coincidencias import EstadoCoincidencias
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.enums.tipo_contacto import TipoContacto
from app.enums.tipo_senal import TipoSenal
from app.filtro_corrupcion.adapters.persistence.senales_json import senales_a_json
from app.filtro_corrupcion.domain.regla_de_escritura import DecisionDeEscritura
from app.filtro_corrupcion.domain.senales_guardadas import construir_senales_guardadas
from app.filtro_corrupcion.domain.tipos import DestinoSiTitular, ReferenciaDerivacion, SenalDetectada, SenalQuejaReclamo
from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia, ResumenCoincidencias
from tests.helpers.corrupcion import un_analisis_clasificado, un_resultado_de_corrupcion


def _decision(confianza: float = 51.67) -> DecisionDeEscritura:
    return DecisionDeEscritura(
        CategoriaIncidencia.QUEJA,
        confianza,
        MotivoDeEscritura.SIN_CORRUPCION,
        CategoriaIncidencia.QUEJA,
        escalar_a_otrans=False,
    )


def _json(**cambios: Any) -> dict[str, Any]:  # noqa: ANN401
    return senales_a_json(construir_senales_guardadas(un_analisis_clasificado(**cambios), _decision()))


def test_el_documento_tiene_las_claves_que_lee_la_consulta_del_analisis() -> None:
    documento = _json()

    assert set(documento) == {
        "senales",
        "faltantes",
        "fichaDerivacion",
        "normas",
        "clasificacion",
        "explicacion",
        "informacionFaltante",
        "decision",
        "modelo",
    }
    assert set(documento["decision"]) == {
        "categoriaEscrita",
        "motivo",
        "propuestaDelAnalisis",
        "confianzaDelAnalisis",
        "confianzaEscrita",
        "escalarAOtrans",
        "requiereRevisionHumana",
        "revisionOtrans",
        "puntajeReglas",
        "puntajeTotal",
        "pesoIa",
    }
    assert documento["modelo"] == {
        "variante": None,
        "degradado": False,
        "motivoDegradado": None,
        "categoriaDelModelo": None,
        "posibleCorrupcion": None,
    }
    assert documento["decision"]["pesoIa"] is None


def test_las_senales_y_las_faltantes_se_escriben_con_sus_valores() -> None:
    reglas = un_resultado_de_corrupcion(senales=(SenalDetectada("coima", TipoSenal.FUERTE, 3),))

    documento = _json(reglas=reglas)

    assert documento["senales"] == [{"frase": "coima", "tipo": "FUERTE", "peso": 3}]
    assert documento["faltantes"] == documento["informacionFaltante"] == []


def test_la_ficha_de_derivacion_lleva_los_contactos_y_el_destino_del_titular() -> None:
    ficha = ReferenciaDerivacion(
        "minsa", (TipoContacto.OCI, TipoContacto.PROCURADOR), DestinoSiTitular("al OCI", "oci"), aplica_al_titular=True
    )
    sin_destino = ReferenciaDerivacion("inr", (), None, aplica_al_titular=False)

    assert _json(reglas=un_resultado_de_corrupcion(referencia_derivacion=ficha))["fichaDerivacion"] == {
        "codigoEntidad": "minsa",
        "contactosDisponibles": ["OCI", "PROCURADOR"],
        "destinoSiTitular": {"texto": "al OCI", "entidadDestinoCodigo": "oci"},
        "aplicaAlTitular": True,
    }
    assert _json(reglas=un_resultado_de_corrupcion(referencia_derivacion=sin_destino))["fichaDerivacion"] == {
        "codigoEntidad": "inr",
        "contactosDisponibles": [],
        "destinoSiTitular": None,
        "aplicaAlTitular": False,
    }


def test_la_clasificacion_lleva_el_mejor_antecedente_y_las_senales_de_queja_y_reclamo() -> None:
    mejor = CandidatoCoincidencia(CategoriaIncidencia.QUEJA, 0.9)
    senal = SenalQuejaReclamo("grosero", CategoriaIncidencia.QUEJA)

    clasificacion = _json(
        coincidencias=ResumenCoincidencias(EstadoCoincidencias.CORROBORADA, mejor, 0.9), senales_queja_reclamo=(senal,)
    )["clasificacion"]

    assert clasificacion["coincidencias"] == {
        "estado": "CORROBORADA",
        "mejor": {"categoria": "QUEJA", "similitud": 0.9},
        "margen": 0.9,
    }
    assert clasificacion["senalesQuejaReclamo"] == [{"frase": "grosero", "categoria": "QUEJA"}]
    assert clasificacion["version"] == "coincidencias-v1"


def test_sin_antecedentes_el_mejor_y_el_margen_quedan_nulos() -> None:
    coincidencias = _json()["clasificacion"]["coincidencias"]

    assert coincidencias == {"estado": "NO_CONSULTADA", "mejor": None, "margen": None}


def test_los_numeros_enteros_se_escriben_sin_decimales_como_lo_hace_el_node() -> None:
    documento = senales_a_json(
        construir_senales_guardadas(
            un_analisis_clasificado(
                coincidencias=ResumenCoincidencias(
                    EstadoCoincidencias.CORROBORADA, CandidatoCoincidencia(CategoriaIncidencia.QUEJA, 1.0), 1.0
                )
            ),
            _decision(95.0),
        )
    )

    texto = json.dumps(documento)
    assert '"confianzaEscrita": 95,' in texto
    assert '"margen": 1}' in texto
    assert '"similitud": 1}' in texto
    assert '"confianzaDelAnalisis": 51.67' in texto
