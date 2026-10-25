from datetime import UTC, datetime

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.resultado_resolucion import ResultadoResolucion
from app.incidencias.adapters.persistence.mapeo import caso_de, fila_de_historial

AHORA = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
CAMPOS_DEL_CASO = [
    "confianza_ia",
    "fecha_creacion",
    "resuelto_en",
    "ahora",
    "revisada",
    "corregida",
    "area_codigo",
    "area_nombre",
    "area_destino_id",
    "area_origen_id",
    "establecimiento_codigo",
    "establecimiento_nombre",
    "establecimiento_nivel",
    "establecimiento_categoria",
    "responsable",
    "medidas_tomadas",
    "fundamento",
    "archivo_detalle",
    "archivado_en",
    "reabierto_en",
    "reabierto_motivo",
    "vence_atencion_en",
    "descripcion_derivacion",
    "descripcion",
    "es_anonimo",
    "dni",
    "nombre",
    "canal",
    "sensible",
]


def _fila_de_caso(**cambios: object) -> dict[str, object]:
    fila: dict[str, object] = dict.fromkeys(CAMPOS_DEL_CASO)
    fila.update(
        id="0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69",
        codigo="MINSA-2026-000001",
        estado="CLASIFICADO",
        categoria="QUEJA",
        categoria_ia=None,
        resultado_resolucion=None,
        motivo_archivo=None,
        descripcion="relato",
        canal="WhatsApp",
        ahora=AHORA,
        fecha_creacion=AHORA,
        revisada=False,
        corregida=False,
        es_anonimo=True,
        sensible=False,
    )
    fila.update(cambios)
    return fila


def test_el_caso_convierte_los_codigos_de_la_base_en_enums_y_deja_los_nulos() -> None:
    caso = caso_de(_fila_de_caso())

    assert caso.estado is EstadoIncidencia.CLASIFICADO
    assert caso.categoria is CategoriaIncidencia.QUEJA
    assert (caso.categoria_ia, caso.resultado_resolucion, caso.motivo_archivo) == (None, None, None)
    assert caso.id == "0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"


def test_el_caso_convierte_resolucion_y_motivo_cuando_existen() -> None:
    caso = caso_de(
        _fila_de_caso(categoria_ia="RECLAMO", resultado_resolucion="ATENDIDO", motivo_archivo="NO_CORRESPONDE")
    )

    assert caso.categoria_ia is CategoriaIncidencia.RECLAMO
    assert caso.resultado_resolucion is ResultadoResolucion.ATENDIDO
    assert caso.motivo_archivo is MotivoArchivo.NO_CORRESPONDE


def test_la_fila_de_historial_convierte_categorias_y_estado() -> None:
    fila = fila_de_historial(
        {
            "operacion": "ACTUALIZACION",
            "actor": "usuario:ana@minsa.gob.pe",
            "actor_nombre": "Ana",
            "fecha_hora": AHORA,
            "ia": False,
            "categoria_ia": None,
            "confianza": None,
            "version": None,
            "corregida": True,
            "categoria_antes": "RECLAMO",
            "categoria_despues": "QUEJA",
            "confirmada": False,
            "estado_nuevo": "DERIVADO",
            "area_antes": None,
            "area_despues": "Hospital A",
            "descripcion_derivacion": None,
            "resolvio": False,
            "reabrio": False,
        }
    )

    assert (fila.categoria_antes, fila.categoria_despues) == (CategoriaIncidencia.RECLAMO, CategoriaIncidencia.QUEJA)
    assert fila.estado_nuevo is EstadoIncidencia.DERIVADO
    assert fila.categoria_ia is None
