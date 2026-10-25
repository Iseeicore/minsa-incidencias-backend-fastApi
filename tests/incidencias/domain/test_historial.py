from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia as C
from app.enums.estado_incidencia import EstadoIncidencia as E
from app.incidencias.domain.fila_historial import FilaHistorial, ItemDeHistorial
from app.incidencias.domain.historial import construir_historial, texto_hace

AHORA = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def hace_horas(horas: int) -> datetime:
    return AHORA - timedelta(hours=horas)


BASE = FilaHistorial(
    operacion="ACTUALIZACION",
    actor="usuario:ana@minsa.gob.pe",
    actor_nombre="Ana Prueba",
    fecha_hora=hace_horas(2),
    ia=False,
    categoria_ia=None,
    confianza=None,
    version=None,
    corregida=False,
    categoria_antes=None,
    categoria_despues=None,
    confirmada=False,
    estado_nuevo=None,
    area_antes=None,
    area_despues=None,
    descripcion_derivacion=None,
    resolvio=False,
    reabrio=False,
)


def fila(**cambios: Any) -> FilaHistorial:  # noqa: ANN401
    return replace(BASE, **cambios)


def construir(filas: list[FilaHistorial]) -> list[ItemDeHistorial]:
    return construir_historial(filas, "WhatsApp", AHORA)


@pytest.mark.parametrize(
    ("horas", "esperado"),
    [
        (0, "hace menos de 1 h"),
        (1, "hace 1 h"),
        (20, "hace 20 h"),
        (47, "hace 47 h"),
        (48, "hace 2 d"),
        (100, "hace 4 d"),
    ],
)
def test_el_tiempo_relativo_pasa_de_horas_a_dias_a_las_48_horas(horas: int, esperado: str) -> None:
    assert texto_hace(horas) == esperado


def test_la_creacion_se_cuenta_como_recibido_por_el_canal() -> None:
    items = construir([fila(operacion="CREACION", actor="ciudadano:abc", actor_nombre=None, fecha_hora=hace_horas(20))])

    assert items == [
        ItemDeHistorial("Recibido por WhatsApp", "Registrado como incidencia.", "hace 20 h", "2026-10-04T16:00:00.000Z")
    ]


def test_la_clasificacion_inicial_conserva_categoria_y_version_sin_presentar_un_porcentaje() -> None:
    [item] = construir(
        [fila(ia=True, categoria_ia=C.RECLAMO, confianza=58, version="v0.3", actor="sistema:ia", actor_nombre=None)]
    )

    assert (item.titulo, item.detalle) == ("Clasificación inicial registrada", "Reclamo (clasificador v0.3).")


def test_la_clasificacion_sin_confianza_ni_version_no_inventa_numeros() -> None:
    [item] = construir([fila(ia=True, categoria_ia=C.QUEJA, actor="sistema:ia", actor_nombre=None)])

    assert item.detalle == "Queja."


def test_la_asignacion_automatica_del_area_al_clasificar_no_se_presenta_como_derivacion_humana() -> None:
    [item] = construir(
        [
            fila(
                ia=True,
                categoria_ia=C.QUEJA,
                area_antes=None,
                area_despues="Hospital A",
                actor="sistema:ia",
                actor_nombre=None,
            )
        ]
    )

    assert (item.titulo, item.detalle) == ("Clasificación inicial registrada", "Queja.")


def test_una_correccion_dice_de_que_categoria_a_cual_y_quien() -> None:
    [item] = construir([fila(corregida=True, categoria_antes=C.RECLAMO, categoria_despues=C.QUEJA)])

    assert (item.titulo, item.detalle) == ("Categoría corregida", "De Reclamo a Queja, por Ana Prueba.")


def test_una_confirmacion_dice_quien_la_hizo() -> None:
    [item] = construir([fila(confirmada=True)])

    assert (item.titulo, item.detalle) == ("Categoría confirmada", "Por Ana Prueba.")


def test_pasar_a_derivado_en_gestion_y_archivado_tienen_su_titulo() -> None:
    items = construir(
        [
            fila(estado_nuevo=E.DERIVADO),
            fila(estado_nuevo=E.EN_GESTION),
            fila(estado_nuevo=E.ARCHIVADO, actor="sistema:vencimiento", actor_nombre=None),
        ]
    )

    assert [item.titulo for item in items] == ["Derivado al área", "Tomado en gestión", "Archivado"]
    assert items[0].detalle == "Por Ana Prueba."
    assert items[2].detalle == "Por Sistema."


def test_una_derivacion_muestra_el_destino_y_una_rederivacion_tambien_el_origen() -> None:
    items = construir(
        [
            fila(estado_nuevo=E.DERIVADO, area_despues="Hospital Dos de Mayo"),
            fila(area_antes="Hospital Dos de Mayo", area_despues="Hospital Loayza"),
        ]
    )

    assert items[0].detalle == "Hacia Hospital Dos de Mayo, por Ana Prueba."
    assert items[1].detalle == "De Hospital Dos de Mayo a Hospital Loayza, por Ana Prueba."


def test_registrar_la_resolucion_gana_sobre_el_cambio_de_estado_que_la_acompana() -> None:
    [item] = construir([fila(resolvio=True, estado_nuevo=E.RESUELTO)])

    assert (item.titulo, item.detalle) == ("Caso resuelto", "Por Ana Prueba.")


def test_conserva_el_motivo_propio_de_cada_derivacion_desde_la_auditoria() -> None:
    items = construir(
        [
            fila(
                area_antes="OTRANS",
                area_despues="Hospital A",
                descripcion_derivacion="Se solicita completar la documentación.",
            ),
            fila(estado_nuevo=E.DERIVADO, descripcion_derivacion="Corresponde atenderlo en esta área."),
        ]
    )

    assert "Motivo: Se solicita completar la documentación." in items[0].detalle
    assert "Motivo: Corresponde atenderlo en esta área." in items[1].detalle
    assert "Corresponde atenderlo" not in items[0].detalle


def test_una_derivacion_sin_motivo_propio_reutiliza_el_ultimo_conocido() -> None:
    motivo = "Se solicita completar la documentación."
    items = construir(
        [
            fila(
                corregida=True,
                categoria_antes=C.DENUNCIA_CORRUPCION,
                categoria_despues=C.QUEJA,
                area_antes="OTRANS",
                area_despues="Hospital A",
                descripcion_derivacion=motivo,
            ),
            fila(estado_nuevo=E.DERIVADO, descripcion_derivacion=None),
        ]
    )

    assert f"Motivo: {motivo}" in items[0].detalle
    assert f"Motivo: {motivo}" in items[1].detalle


def test_reabrir_un_caso_tiene_su_propio_titulo_aunque_el_estado_que_acompana_sea_en_gestion() -> None:
    [item] = construir([fila(reabrio=True, estado_nuevo=E.EN_GESTION)])

    assert (item.titulo, item.detalle) == ("Caso reabierto", "Por Ana Prueba.")


def test_un_actor_que_no_es_persona_ni_sistema_no_se_revela() -> None:
    [item] = construir([fila(confirmada=True, actor="operador:gestor", actor_nombre=None)])

    assert item.detalle == "Por una persona."


def test_ignora_los_cambios_que_no_son_un_hito_y_conserva_el_orden_recibido() -> None:
    items = construir(
        [
            fila(ia=True, categoria_ia=C.QUEJA, fecha_hora=hace_horas(10)),
            fila(fecha_hora=hace_horas(9)),
            fila(confirmada=True, fecha_hora=hace_horas(8)),
        ]
    )

    assert [item.titulo for item in items] == ["Clasificación inicial registrada", "Categoría confirmada"]


@pytest.mark.parametrize(
    ("cambios", "titulo", "detalle"),
    [
        (
            {"resolvio": True, "reabrio": True, "estado_nuevo": E.ARCHIVADO, "ia": True},
            "Caso resuelto",
            "Por Ana Prueba.",
        ),
        ({"reabrio": True, "estado_nuevo": E.ARCHIVADO, "ia": True}, "Caso reabierto", "Por Ana Prueba."),
        ({"estado_nuevo": E.ARCHIVADO, "ia": True}, "Archivado", "Por Ana Prueba."),
        ({"ia": True, "area_despues": "B", "corregida": True}, "Clasificación inicial registrada", "Clasificado."),
        (
            {"area_antes": "A", "area_despues": "B", "estado_nuevo": E.DERIVADO, "descripcion_derivacion": "m"},
            "Derivado al área",
            "De A a B, por Ana Prueba. Motivo: m",
        ),
        ({"area_despues": "B", "corregida": True}, "Derivado al área", "Hacia B, por Ana Prueba."),
        (
            {"area_antes": "B", "area_despues": "B", "estado_nuevo": E.DERIVADO, "descripcion_derivacion": "m"},
            "Derivado al área",
            "Por Ana Prueba. Motivo: m",
        ),
        ({"estado_nuevo": E.DERIVADO}, "Derivado al área", "Por Ana Prueba."),
        ({"estado_nuevo": E.EN_GESTION, "corregida": True}, "Tomado en gestión", "Por Ana Prueba."),
        (
            {"corregida": True, "confirmada": True},
            "Categoría corregida",
            "De sin categoría a sin categoría, por Ana Prueba.",
        ),
        ({"confirmada": True, "estado_nuevo": E.RESUELTO}, "Categoría confirmada", "Por Ana Prueba."),
    ],
    ids=[
        "resolucion",
        "reapertura",
        "archivo",
        "clasificacion",
        "rederivacion-con-motivo",
        "derivacion-sin-origen",
        "area-sin-cambio",
        "estado-derivado-sin-motivo",
        "toma",
        "correccion-sin-categorias",
        "confirmacion",
    ],
)
def test_describe_cada_hito_segun_el_orden_de_prioridad(cambios: dict[str, Any], titulo: str, detalle: str) -> None:
    [item] = construir([fila(**cambios, fecha_hora=hace_horas(3))])

    assert item == ItemDeHistorial(titulo, detalle, "hace 3 h", "2026-10-05T09:00:00.000Z")


def test_un_cambio_sin_hito_se_omite() -> None:
    items = construir(
        [fila(estado_nuevo=E.RESUELTO), fila(area_antes="B", area_despues="B"), fila(estado_nuevo=E.CLASIFICADO)]
    )

    assert items == []


def test_nunca_devuelve_el_identificador_del_actor() -> None:
    texto = repr(construir([fila(confirmada=True), fila(estado_nuevo=E.DERIVADO)]))

    assert "ana@minsa.gob.pe" not in texto
    assert "usuario:" not in texto
