from app.enums.categoria_api import CategoriaApi
from app.enums.grupo_cita import GrupoCita
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.enums.tipo_contacto import TipoContacto
from app.enums.variante_ia import VarianteIa
from app.incidencias.application.armar_analisis import armar_analisis
from app.shared.normas import FragmentoNorma
from tests.helpers.analisis_en_memoria import una_fila_de_analisis

CODIGO = "MINSA-2026-000001"
FRAGMENTOS = {
    "ANEXO_C-III-a": FragmentoNorma(
        "ANEXO_C-III-a",
        "F",
        "Anexo C III a",
        "Cohecho",
        "DELITO",
        "Texto del cohecho",
        cita_automatica=True,
        motivo_sin_cita=None,
    ),
    "AM-REQ-PRUEBAS": FragmentoNorma(
        "AM-REQ-PRUEBAS",
        "F",
        "Ayuda memoria, pruebas",
        "Pruebas",
        "PROCEDIMIENTO",
        "Aporte pruebas",
        cita_automatica=True,
        motivo_sin_cita=None,
    ),
}
SENALES = {
    "senales": [{"frase": "me pidió plata", "tipo": "FUERTE", "peso": 3}],
    "explicacion": "Hay un pedido de dinero.",
    "informacionFaltante": ["pruebas", "hecho_detallado"],
    "fichaDerivacion": {"codigoEntidad": "sis", "contactosDisponibles": ["OCI"], "aplicaAlTitular": False},
    "normas": {
        "version": "normas-v1",
        "transcripcionAnexoCCotejada": True,
        "sinSupuestoIdentificado": False,
        "citas": [
            {
                "fragmentoId": "ANEXO_C-III-a",
                "referencia": "guardada",
                "grupo": "SUPUESTO",
                "senalesQueLaMotivan": ["x"],
            },
            {"fragmentoId": "AM-DESCONOCIDO", "referencia": "Ayuda memoria guardada", "grupo": "PROCEDIMIENTO"},
        ],
    },
    "decision": {
        "motivo": "REGLAS",
        "propuestaDelAnalisis": "DENUNCIA_CORRUPCION",
        "escalarAOtrans": False,
        "requiereRevisionHumana": True,
        "pesoIa": None,
    },
    "modelo": {"variante": "V2C", "degradado": False},
}


def test_arma_el_analisis_completo_con_las_citas_enriquecidas_con_el_texto_de_las_normas() -> None:
    analisis = armar_analisis(CODIGO, una_fila_de_analisis(senales=SENALES), FRAGMENTOS)

    assert (analisis.codigo, analisis.categoria_ia, analisis.confianza_ia) == (
        CODIGO,
        CategoriaApi.DENUNCIA_CORRUPCION,
        82.0,
    )
    assert (analisis.version_clasificador, analisis.version_reglas, analisis.puntaje) == (
        "coincidencias-v1",
        "reglas-corrupcion-v1.3",
        5,
    )
    assert analisis.motivo_de_escritura == MotivoDeEscritura.REGLAS
    assert analisis.propuesta_del_analisis == CategoriaApi.DENUNCIA_CORRUPCION
    assert (analisis.requiere_revision_humana, analisis.escalar_a_otrans) == (True, False)
    assert analisis.explicacion == "Hay un pedido de dinero."
    [supuesto] = analisis.supuestos
    assert (supuesto.referencia, supuesto.titulo, supuesto.texto) == ("Anexo C III a", "Cohecho", "Texto del cohecho")
    assert supuesto.senales_que_la_motivan == ("x",)
    assert supuesto.grupo == GrupoCita.SUPUESTO


def test_una_cita_de_un_fragmento_que_ya_no_existe_conserva_su_referencia_guardada_y_no_trae_texto() -> None:
    analisis = armar_analisis(CODIGO, una_fila_de_analisis(senales=SENALES), FRAGMENTOS)

    [procedimiento] = analisis.procedimiento
    assert (procedimiento.referencia, procedimiento.titulo, procedimiento.texto) == (
        "Ayuda memoria guardada",
        "Ayuda memoria guardada",
        None,
    )
    assert procedimiento.grupo == GrupoCita.PROCEDIMIENTO


def test_los_requisitos_faltantes_salen_solo_si_el_fragmento_existe() -> None:
    analisis = armar_analisis(CODIGO, una_fila_de_analisis(senales=SENALES), FRAGMENTOS)

    [requisito] = analisis.requisitos_faltantes
    assert (requisito.codigo, requisito.referencia, requisito.texto) == (
        "pruebas",
        "Ayuda memoria, pruebas",
        "Aporte pruebas",
    )


def test_trae_las_normas_el_modelo_y_la_ficha_de_derivacion_guardados() -> None:
    analisis = armar_analisis(CODIGO, una_fila_de_analisis(senales=SENALES), FRAGMENTOS)

    assert analisis.version_normas == "normas-v1"
    assert analisis.etiqueta_normas == "Referencia orientativa; la califica OTRANS."
    assert analisis.transcripcion_anexo_c_cotejada is True
    assert analisis.sin_supuesto_identificado is False
    assert (analisis.modelo.variante, analisis.modelo.degradado, analisis.modelo.peso_ia) == (
        VarianteIa.V2C,
        False,
        None,
    )
    assert analisis.ficha_derivacion is not None
    assert analisis.ficha_derivacion.contactos_disponibles == (TipoContacto.OCI,)


def test_lo_que_el_analisis_no_guardo_sale_vacio_o_en_falso() -> None:
    analisis = armar_analisis(
        CODIGO, una_fila_de_analisis(senales="basura", categoria_ia=None, confianza_ia=None), FRAGMENTOS
    )

    assert (analisis.categoria_ia, analisis.confianza_ia) == (None, None)
    assert (analisis.motivo_de_escritura, analisis.propuesta_del_analisis) == (None, None)
    assert (analisis.requiere_revision_humana, analisis.escalar_a_otrans, analisis.sin_supuesto_identificado) == (
        False,
        False,
        False,
    )
    assert analisis.senales == ()
    assert (analisis.supuestos, analisis.procedimiento, analisis.requisitos_faltantes) == ((), (), ())
    assert (analisis.version_normas, analisis.ficha_derivacion) == (None, None)
    assert analisis.transcripcion_anexo_c_cotejada is False
    assert (analisis.modelo.variante, analisis.modelo.degradado, analisis.modelo.peso_ia) == (None, False, None)
    assert analisis.etiqueta_normas == "Referencia orientativa; la califica OTRANS."


def test_el_area_mencionada_exige_codigo_y_nombre() -> None:
    con_area = armar_analisis(
        CODIGO,
        una_fila_de_analisis(area_mencionada_codigo="HOSP-01", area_mencionada_nombre="Hospital Uno"),
        FRAGMENTOS,
    )
    sin_nombre = armar_analisis(CODIGO, una_fila_de_analisis(area_mencionada_codigo="HOSP-01"), FRAGMENTOS)

    assert con_area.area_mencionada is not None
    assert (con_area.area_mencionada.codigo, con_area.area_mencionada.nombre) == ("HOSP-01", "Hospital Uno")
    assert sin_nombre.area_mencionada is None


def test_la_fecha_del_analisis_sale_en_iso_con_milisegundos_y_los_datos_mencionados_pasan_tal_cual() -> None:
    analisis = armar_analisis(
        CODIGO, una_fila_de_analisis(nombre_mencionado="Ana", cargo_mencionado="jefa"), FRAGMENTOS
    )

    assert analisis.fecha_analisis == "2026-10-24T12:00:00.789Z"
    assert (analisis.cargo_mencionado, analisis.nombre_mencionado) == ("jefa", "Ana")


def test_sin_fragmentos_explicitos_usa_los_datos_de_normas_del_proyecto() -> None:
    senales = {
        "normas": {
            "version": "normas-v1",
            "citas": [{"fragmentoId": "ANEXO_C-I-a", "referencia": "x", "grupo": "SUPUESTO"}],
        }
    }

    analisis = armar_analisis(CODIGO, una_fila_de_analisis(senales=senales))

    assert analisis.supuestos[0].titulo == "Conflicto de intereses"
    assert analisis.supuestos[0].texto is not None
