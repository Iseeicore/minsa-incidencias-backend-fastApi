from app.enums.categoria_api import CategoriaApi
from app.enums.estado_api import EstadoApi
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.incidencias.application.armar_derivacion import resumir_derivacion
from tests.helpers.builders import una_derivacion_consultada


def test_el_resumen_traduce_categoria_y_estado_al_contrato_y_la_fecha_a_milisegundos() -> None:
    resumen = resumir_derivacion(una_derivacion_consultada())

    assert (resumen.id, resumen.codigo_caso) == ("4821", "MINSA-2026-000001")
    assert resumen.fecha_derivacion == "2026-10-24T09:30:15.123Z"
    assert (resumen.categoria, resumen.estado) == (CategoriaApi.RECLAMO, EstadoApi.DERIVADO)


def test_el_resumen_lleva_el_origen_el_destino_y_quien_lo_envio() -> None:
    resumen = resumir_derivacion(una_derivacion_consultada())

    assert (resumen.origen.codigo, resumen.origen.nombre) == ("OTRANS", "Oficina de Transparencia")
    assert (resumen.destino.codigo, resumen.destino.nombre, resumen.destino.codigo_renipress) == (
        "EESS-0001",
        "Centro de Salud Uno",
        "1",
    )
    assert (resumen.derivado_por, resumen.descripcion) == ("Lucía Ramos", "Corresponde a un reclamo.")


def test_un_envio_sin_usuario_conocido_dice_usuario_no_disponible() -> None:
    resumen = resumir_derivacion(una_derivacion_consultada(derivado_por=None))

    assert resumen.derivado_por == "Usuario no disponible"


def test_un_nombre_vacio_se_conserva_como_viene() -> None:
    assert resumir_derivacion(una_derivacion_consultada(derivado_por="")).derivado_por == ""


def test_un_envio_sin_categoria_ni_descripcion_deja_esos_campos_nulos() -> None:
    resumen = resumir_derivacion(una_derivacion_consultada(categoria=None, descripcion=None, destino_renipress=None))

    assert (resumen.categoria, resumen.descripcion, resumen.destino.codigo_renipress) == (None, None, None)


def test_un_caso_archivado_conserva_el_motivo_de_archivo() -> None:
    resumen = resumir_derivacion(
        una_derivacion_consultada(estado=EstadoIncidencia.ARCHIVADO, motivo_archivo=MotivoArchivo.NO_CORRESPONDE)
    )

    assert (resumen.estado, resumen.motivo_archivo) == (EstadoApi.ARCHIVADO, MotivoArchivo.NO_CORRESPONDE)
