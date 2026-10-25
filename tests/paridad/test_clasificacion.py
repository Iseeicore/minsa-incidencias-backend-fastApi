import json
from pathlib import Path
from typing import Any

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.filtro_corrupcion.adapters.http.schemas import EvaluacionRequest
from app.filtro_corrupcion.adapters.persistence.senales_json import senales_a_json
from app.filtro_corrupcion.application.analizar_caso import CasoAnalizado, analizar_caso
from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia

CORPUS_DEL_NODO = Path(__file__).parents[1] / "fixtures" / "corpus_clasificacion_node.json"


def _casos() -> list[dict[str, Any]]:
    casos: list[dict[str, Any]] = json.loads(CORPUS_DEL_NODO.read_text(encoding="utf-8"))
    return casos


def _documento(analizado: CasoAnalizado) -> dict[str, Any]:
    reglas = analizado.reglas
    return {
        "categoria": analizado.decision.categoria.value,
        "confianza": analizado.decision.confianza,
        "motivo": analizado.decision.motivo.value,
        "version": analizado.version,
        "puntaje": reglas.puntaje,
        "versionReglas": reglas.version_reglas,
        "cargoMencionado": reglas.actor.cargo if reglas.actor else None,
        "nombreMencionado": reglas.nombre_mencionado,
        "entidad": reglas.entidad.codigo if reglas.entidad else None,
        "senales": senales_a_json(analizado.senales),
    }


async def _analizar(entrada: dict[str, Any]) -> dict[str, Any]:
    contexto = (
        EvaluacionRequest.model_validate({"texto": entrada["texto"], **entrada["contexto"]}).a_solicitud().contexto
    )
    candidatos = entrada["candidatos"]
    if candidatos is None:
        return _documento(await analizar_caso(entrada["texto"], contexto, None))
    lista = [CandidatoCoincidencia(CategoriaIncidencia(c["categoria"]), c["similitud"]) for c in candidatos]

    async def buscar(_texto: str) -> list[CandidatoCoincidencia]:
        return lista

    return _documento(await analizar_caso(entrada["texto"], contexto, buscar))


def test_el_corpus_de_oro_cubre_las_ramas_importantes_del_clasificador() -> None:
    esperados = [caso["esperado"] for caso in _casos()]
    clasificaciones = [e["senales"]["clasificacion"] for e in esperados]

    assert len(esperados) > 600
    assert {e["categoria"] for e in esperados} == {"DENUNCIA_CORRUPCION", "QUEJA", "RECLAMO", "OTRO"}
    assert {e["motivo"] for e in esperados} == {"REGLAS", "IDENTIDAD", "DUDA_SIN_MODELO", "SIN_CORRUPCION"}
    assert {c["coincidencias"]["estado"] for c in clasificaciones} == {
        "NO_CONSULTADA",
        "CORROBORADA",
        "SIN_CANDIDATOS",
        "INSUFICIENTE",
        "CONTRADICTORIA",
    }
    assert {c["origen"] for c in clasificaciones} == {"REGLAS", "REGLAS_CON_APOYO_BD", "SIN_COINCIDENCIAS"}
    assert any(e["senales"]["fichaDerivacion"] for e in esperados)
    assert any(e["senales"]["normas"]["sinSupuestoIdentificado"] for e in esperados)
    assert any(e["senales"]["decision"]["escalarAOtrans"] for e in esperados)
    assert any(e["entidad"] for e in esperados)


async def test_el_clasificador_escribe_exactamente_lo_mismo_que_el_node_en_todo_el_corpus() -> None:
    distintos: list[int] = []
    for numero, caso in enumerate(_casos()):
        if await _analizar(caso["entrada"]) != caso["esperado"]:
            distintos.append(numero)

    assert distintos == []
