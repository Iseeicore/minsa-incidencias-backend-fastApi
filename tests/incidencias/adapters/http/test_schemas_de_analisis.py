from typing import Any

from app.incidencias.adapters.http.schemas_de_analisis import AnalisisIaResponse
from app.incidencias.application.armar_analisis import armar_analisis
from tests.helpers.analisis_en_memoria import una_fila_de_analisis

SENALES = {
    "senales": [{"frase": "me pidió plata", "tipo": "FUERTE", "peso": 3}],
    "explicacion": "Hay un pedido de dinero.",
    "informacionFaltante": ["pruebas"],
    "fichaDerivacion": {
        "codigoEntidad": "sis",
        "contactosDisponibles": ["OCI"],
        "destinoSiTitular": {"texto": "A la PCM", "entidadDestinoCodigo": "pcm"},
        "aplicaAlTitular": True,
    },
    "normas": {
        "version": "normas-v1",
        "citas": [{"fragmentoId": "ANEXO_C-I-a", "referencia": "x", "grupo": "SUPUESTO", "senalesQueLaMotivan": ["a"]}],
    },
    "decision": {"motivo": "REGLAS", "propuestaDelAnalisis": "QUEJA", "requiereRevisionHumana": True, "pesoIa": 2.5},
    "modelo": {"variante": "V2", "degradado": True},
}


def _cuerpo(**cambios: object) -> dict[str, Any]:
    analisis = armar_analisis("MINSA-2026-000001", una_fila_de_analisis(**cambios))
    return AnalisisIaResponse.desde_dominio(analisis).model_dump(by_alias=True, mode="json")


def test_el_analisis_se_serializa_con_los_nombres_del_contrato() -> None:
    cuerpo = _cuerpo(
        senales=SENALES, nombre_mencionado="Ana", area_mencionada_codigo="HOSP-01", area_mencionada_nombre="Hospital"
    )

    assert cuerpo["categoriaIa"] == "denuncia-corrupcion"
    assert cuerpo["propuestaDelAnalisis"] == "queja"
    assert cuerpo["motivoDeEscritura"] == "REGLAS"
    assert cuerpo["senales"] == [{"frase": "me pidió plata", "tipo": "FUERTE", "peso": 3}]
    assert cuerpo["fichaDerivacion"] == {
        "codigoEntidad": "sis",
        "contactosDisponibles": ["OCI"],
        "destinoSiTitular": {"texto": "A la PCM", "entidadDestinoCodigo": "pcm"},
        "aplicaAlTitular": True,
    }
    assert cuerpo["areaMencionada"] == {"codigo": "HOSP-01", "nombre": "Hospital"}
    assert cuerpo["modelo"] == {"variante": "V2", "degradado": True, "pesoIa": 2.5}
    assert cuerpo["fechaAnalisis"] == "2026-10-24T12:00:00.789Z"


def test_las_citas_y_los_requisitos_salen_con_el_texto_de_las_normas() -> None:
    cuerpo = _cuerpo(senales=SENALES)

    [supuesto] = cuerpo["supuestos"]
    assert supuesto["titulo"] == "Conflicto de intereses"
    assert supuesto["senalesQueLaMotivan"] == ["a"]
    assert cuerpo["requisitosFaltantes"][0]["codigo"] == "pruebas"


def test_un_analisis_sin_nada_guardado_sale_con_nulos_y_listas_vacias() -> None:
    cuerpo = _cuerpo(senales={}, categoria_ia=None, confianza_ia=None, cargo_mencionado=None)

    assert cuerpo["fichaDerivacion"] is None
    assert cuerpo["areaMencionada"] is None
    assert cuerpo["modelo"] == {"variante": None, "degradado": False, "pesoIa": None}
    assert (cuerpo["senales"], cuerpo["supuestos"], cuerpo["procedimiento"]) == ([], [], [])
