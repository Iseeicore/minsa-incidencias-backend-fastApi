from datetime import UTC, datetime

from app.enums.accion_incidencia import AccionIncidencia
from app.enums.categoria_api import CategoriaApi
from app.enums.estado_api import EstadoApi
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.plazo_estado import PlazoEstado
from app.enums.resultado_resolucion import ResultadoResolucion
from app.incidencias.application.armar_caso import detallar, resumir
from app.incidencias.domain.plazo import PlazosConfigurados
from tests.helpers.builders import un_caso_consultado, una_evidencia, una_sesion

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
GESTOR = una_sesion(roles=("GESTOR",))


def test_el_resumen_traduce_los_codigos_de_la_base_a_los_de_la_api() -> None:
    resumen = resumir(un_caso_consultado(), GESTOR, PLAZOS)

    assert resumen.codigo == "MINSA-2026-000001"
    assert (resumen.categoria, resumen.categoria_ia, resumen.estado) == (
        CategoriaApi.RECLAMO,
        CategoriaApi.RECLAMO,
        EstadoApi.CLASIFICADO,
    )
    assert resumen.area is not None
    assert (resumen.area.codigo, resumen.area.nombre) == ("HOSP-01", "Hospital Uno")
    assert resumen.establecimiento is not None
    assert resumen.establecimiento.codigo_renipress == "1234"
    assert resumen.horas_desde_llegada == 5
    assert resumen.horas_desde_resolucion is None
    assert resumen.plazo.estado is PlazoEstado.EN_PLAZO
    assert resumen.acciones == (AccionIncidencia.CONFIRMAR, AccionIncidencia.CORREGIR, AccionIncidencia.ARCHIVAR)


def test_sin_sesion_el_resumen_no_trae_acciones() -> None:
    assert resumir(un_caso_consultado(), None, PLAZOS).acciones == ()


def test_un_caso_sin_categoria_ni_area_ni_establecimiento_deja_esos_campos_nulos() -> None:
    caso = un_caso_consultado(
        categoria=None,
        categoria_ia=None,
        area_codigo=None,
        area_nombre=None,
        establecimiento_codigo=None,
        establecimiento_nombre=None,
    )

    resumen = resumir(caso, GESTOR, PLAZOS)

    assert (resumen.categoria, resumen.categoria_ia, resumen.area, resumen.establecimiento) == (None, None, None, None)


def test_las_horas_nunca_son_negativas() -> None:
    caso = un_caso_consultado(
        fecha_creacion=datetime(2026, 10, 25, tzinfo=UTC), resuelto_en=datetime(2026, 10, 26, tzinfo=UTC)
    )

    resumen = resumir(caso, GESTOR, PLAZOS)

    assert (resumen.horas_desde_llegada, resumen.horas_desde_resolucion) == (0, 0)


def test_el_detalle_agrega_resolucion_archivo_reapertura_reclamante_evidencias_e_historial() -> None:
    caso = un_caso_consultado(
        estado=EstadoIncidencia.ARCHIVADO,
        medidas_tomadas="medidas",
        fundamento="fundamento",
        resultado_resolucion=ResultadoResolucion.ATENDIDO,
        motivo_archivo=MotivoArchivo.NO_CORRESPONDE,
        archivo_detalle=None,
        archivado_en=datetime(2026, 10, 24, 10, 0, tzinfo=UTC),
        reabierto_en=datetime(2026, 10, 24, 11, 0, tzinfo=UTC),
        reabierto_motivo="por reclamo",
        es_anonimo=False,
        nombre="Luis Alberto Quispe",
        dni="12345678",
        sensible=True,
    )
    evidencias = [
        una_evidencia(nombre=None),
        una_evidencia(
            "1b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69",
            "foto.png",
            "VIDEO",
            "Video",
            verificada=False,
            contenido_disponible=False,
        ),
    ]

    detalle = detallar(caso, GESTOR, PLAZOS, evidencias, [])

    assert detalle.resolucion is not None
    assert (detalle.resolucion.medidas_tomadas, detalle.resolucion.resultado) == (
        "medidas",
        ResultadoResolucion.ATENDIDO,
    )
    assert detalle.archivo is not None
    assert (detalle.archivo.motivo, detalle.archivo.detalle, detalle.archivo.archivado_en) == (
        MotivoArchivo.NO_CORRESPONDE,
        None,
        "2026-10-24T10:00:00.000Z",
    )
    assert detalle.reapertura is not None
    assert (detalle.reapertura.reabierto_en, detalle.reapertura.motivo) == ("2026-10-24T11:00:00.000Z", "por reclamo")
    assert detalle.reclamante == "Luis A. · DNI ••••5678"
    assert [(e.nombre, e.tipo, e.sensible, e.contenido_disponible) for e in detalle.evidencias] == [
        ("Imagen 1", "imagen", True, True),
        ("foto.png", "video", True, False),
    ]
    assert detalle.historial == ()


def test_un_detalle_sin_resolucion_archivo_ni_reapertura_los_deja_nulos() -> None:
    detalle = detallar(un_caso_consultado(), GESTOR, PLAZOS, [], [])

    assert (detalle.resolucion, detalle.archivo, detalle.reapertura) == (None, None, None)
    assert detalle.reclamante == "Anónimo"
    assert detalle.descripcion == "Relato del caso."
