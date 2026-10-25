from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.filtro_corrupcion.domain.senales_guardadas import SenalesGuardadas
    from app.filtro_corrupcion.domain.tipos import ReferenciaDerivacion
    from app.filtro_corrupcion.domain.tipos_de_clasificacion import ResumenCoincidencias
    from app.filtro_corrupcion.domain.trazabilidad_normas import CitaDeNormaClasificada

MODELO_AUSENTE: dict[str, Any] = {
    "variante": None,
    "degradado": False,
    "motivoDegradado": None,
    "categoriaDelModelo": None,
    "posibleCorrupcion": None,
}


def _numero(valor: float | None) -> int | float | None:
    if valor is None:
        return None
    return int(valor) if float(valor).is_integer() else valor


def _ficha(ficha: ReferenciaDerivacion | None) -> dict[str, Any] | None:
    if ficha is None:
        return None
    destino = ficha.destino_si_titular
    return {
        "codigoEntidad": ficha.codigo_entidad,
        "contactosDisponibles": [contacto.value for contacto in ficha.contactos_disponibles],
        "destinoSiTitular": (
            {"texto": destino.texto, "entidadDestinoCodigo": destino.entidad_destino_codigo}
            if destino is not None
            else None
        ),
        "aplicaAlTitular": ficha.aplica_al_titular,
    }


def _cita(cita: CitaDeNormaClasificada) -> dict[str, Any]:
    return {
        "fragmentoId": cita.fragmento_id,
        "referencia": cita.referencia,
        "grupo": cita.grupo.value,
        "senalesQueLaMotivan": list(cita.senales_que_la_motivan),
    }


def _coincidencias(resumen: ResumenCoincidencias) -> dict[str, Any]:
    mejor = resumen.mejor
    return {
        "estado": resumen.estado.value,
        "mejor": (
            {"categoria": mejor.categoria.value, "similitud": _numero(mejor.similitud)} if mejor is not None else None
        ),
        "margen": _numero(resumen.margen),
    }


def senales_a_json(guardadas: SenalesGuardadas) -> dict[str, Any]:
    decision = guardadas.decision
    clasificacion = guardadas.clasificacion
    faltantes = [faltante.value for faltante in guardadas.informacion_faltante]
    return {
        "senales": [{"frase": s.frase, "tipo": s.tipo.value, "peso": s.peso} for s in guardadas.senales],
        "faltantes": faltantes,
        "fichaDerivacion": _ficha(guardadas.ficha_derivacion),
        "normas": {
            "version": guardadas.normas.version,
            "etiqueta": guardadas.normas.etiqueta,
            "transcripcionAnexoCCotejada": guardadas.normas.transcripcion_anexo_c_cotejada,
            "sinSupuestoIdentificado": guardadas.normas.sin_supuesto_identificado,
            "citas": [_cita(cita) for cita in guardadas.normas.citas],
        },
        "clasificacion": {
            "version": clasificacion.version,
            "origen": clasificacion.origen.value,
            "coincidencias": _coincidencias(clasificacion.coincidencias),
            "senalesQuejaReclamo": [
                {"frase": s.frase, "categoria": s.categoria.value} for s in clasificacion.senales_queja_reclamo
            ],
        },
        "explicacion": guardadas.explicacion,
        "informacionFaltante": faltantes,
        "decision": {
            "categoriaEscrita": decision.categoria_escrita.value,
            "motivo": decision.motivo.value,
            "propuestaDelAnalisis": decision.propuesta_del_analisis.value,
            "confianzaDelAnalisis": _numero(decision.confianza_del_analisis),
            "confianzaEscrita": _numero(decision.confianza_escrita),
            "escalarAOtrans": decision.escalar_a_otrans,
            "requiereRevisionHumana": decision.requiere_revision_humana,
            "revisionOtrans": decision.revision_otrans,
            "puntajeReglas": decision.puntaje_reglas,
            "puntajeTotal": decision.puntaje_total,
            "pesoIa": None,
        },
        "modelo": dict(MODELO_AUSENTE),
    }
