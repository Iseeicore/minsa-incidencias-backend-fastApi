from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.resultado_resolucion import ResultadoResolucion
from app.enums.tipo_area import TipoArea
from app.shared.sesion import SesionActual
from tests.helpers.app_factory import un_cliente, un_contenedor
from tests.helpers.builders import un_caso_consultado, una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

CODIGO = "MINSA-2026-000001"
RUTA = f"/v1/incidencias/{CODIGO}"
GESTOR = una_sesion(roles=("GESTOR",))
TEXTO = "Texto de al menos diez"


def _cliente(
    lector: IncidenciasEnMemoria | None = None, sesion: SesionActual = GESTOR, *, con_sesion: bool = True
) -> AsyncClient:
    contenedor = un_contenedor(incidencias=lector or IncidenciasEnMemoria([un_caso_consultado()]))
    return un_cliente(contenedor, con_sesion=con_sesion, sesion=sesion)


async def test_confirmar_responde_el_mensaje_y_el_caso_sin_necesitar_cuerpo() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()])
    async with _cliente(lector) as cliente:
        respuesta = await cliente.post(f"{RUTA}/confirmar")

    cuerpo = respuesta.json()
    assert respuesta.status_code == HTTPStatus.OK
    assert cuerpo["mensaje"] == "Categoría confirmada."
    assert cuerpo["caso"]["codigo"] == CODIGO
    assert ("confirmar", ("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",)) in lector.llamadas
    assert lector.actores == ["usuario:gestor@minsa.gob.pe"]


async def test_confirmar_acepta_un_cuerpo_vacio_con_campos_de_mas() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post(f"{RUTA}/confirmar", json={"sobra": True})

    assert respuesta.status_code == HTTPStatus.OK


async def test_un_cuerpo_que_no_es_un_objeto_responde_400() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post(f"{RUTA}/confirmar", json=[1])

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["errorCode"] == "VALIDATION_FAILED"


async def test_corregir_pasa_la_categoria_traducida_al_dominio() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()])
    async with _cliente(lector) as cliente:
        respuesta = await cliente.post(f"{RUTA}/corregir", json={"categoria": "queja"})

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()["mensaje"] == "Categoría corregida."
    assert ("corregir", ("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", CategoriaIncidencia.QUEJA, None)) in lector.llamadas


async def test_corregir_a_denuncia_que_saca_el_caso_de_la_vista_responde_enviado_a_otrans() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()])
    lector.ocultar_al_cerrar = True
    async with _cliente(lector) as cliente:
        respuesta = await cliente.post(f"{RUTA}/corregir", json={"categoria": "denuncia-corrupcion"})

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == {"codigo": CODIGO, "enviadoAOtrans": True}


async def test_corregir_a_otra_categoria_que_saca_el_caso_de_la_vista_responde_caso_nulo() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()])
    lector.ocultar_al_cerrar = True
    async with _cliente(lector) as cliente:
        respuesta = await cliente.post(f"{RUTA}/corregir", json={"categoria": "otro"})

    assert respuesta.json() == {
        "mensaje": "Categoría corregida a Otro. El caso pasó al área correspondiente y ya no aparece en tu lista.",
        "caso": None,
    }


async def test_derivar_pasa_la_descripcion_y_el_area_vinculada() -> None:
    caso = un_caso_consultado(revisada=True)
    lector = IncidenciasEnMemoria([caso])
    lector.areas_por_id[(1, TipoArea.ESTABLECIMIENTO)] = 1
    async with _cliente(lector) as cliente:
        respuesta = await cliente.post(f"{RUTA}/derivar", json={"descripcionDerivacion": TEXTO})

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()["mensaje"] == "Caso derivado al área."
    assert ("derivar", (caso.id, 1, TEXTO)) in lector.llamadas


async def test_tomar_pasa_el_caso_a_en_gestion() -> None:
    caso = un_caso_consultado(revisada=True)
    lector = IncidenciasEnMemoria([caso])
    async with _cliente(lector) as cliente:
        respuesta = await cliente.post(f"{RUTA}/tomar")

    assert respuesta.json()["mensaje"] == "Caso tomado en gestión."
    assert ("cambiar_estado", (caso.id, EstadoIncidencia.EN_GESTION)) in lector.llamadas


async def test_resolver_registra_la_resolucion() -> None:
    caso = un_caso_consultado(estado=EstadoIncidencia.EN_GESTION)
    lector = IncidenciasEnMemoria([caso])
    cuerpo = {"medidasTomadas": TEXTO, "fundamento": TEXTO, "resultado": "ATENDIDO"}
    async with _cliente(lector) as cliente:
        respuesta = await cliente.post(f"{RUTA}/resolver", json=cuerpo)

    assert respuesta.json()["mensaje"] == "Caso resuelto."
    assert ("resolver", (caso.id, TEXTO, TEXTO, ResultadoResolucion.ATENDIDO)) in lector.llamadas


async def test_archivar_registra_el_motivo_manual() -> None:
    caso = un_caso_consultado()
    lector = IncidenciasEnMemoria([caso])
    async with _cliente(lector) as cliente:
        respuesta = await cliente.post(f"{RUTA}/archivar", json={"motivo": "NO_CORRESPONDE", "detalle": TEXTO})

    assert respuesta.json()["mensaje"] == "Caso archivado."
    assert ("archivar", (caso.id, MotivoArchivo.NO_CORRESPONDE, TEXTO)) in lector.llamadas


async def test_reabrir_registra_el_motivo_de_la_reapertura() -> None:
    caso = un_caso_consultado(estado=EstadoIncidencia.ARCHIVADO)
    lector = IncidenciasEnMemoria([caso])
    async with _cliente(lector) as cliente:
        respuesta = await cliente.post(f"{RUTA}/reabrir", json={"motivo": TEXTO})

    assert respuesta.json()["mensaje"] == "Caso reabierto. Quedó en gestión."
    assert ("reabrir", (caso.id, TEXTO)) in lector.llamadas


@pytest.mark.parametrize(
    ("accion", "cuerpo"),
    [
        ("corregir", {}),
        ("derivar", {"descripcionDerivacion": "corta"}),
        ("resolver", {"medidasTomadas": TEXTO}),
        ("archivar", {"motivo": "VENCIDA_SIN_ATENDER", "detalle": TEXTO}),
        ("reabrir", {"motivo": "corto"}),
    ],
)
async def test_un_cuerpo_invalido_responde_400_con_detalles_y_no_toca_la_base(
    accion: str, cuerpo: dict[str, object]
) -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()])
    async with _cliente(lector) as cliente:
        respuesta = await cliente.post(f"{RUTA}/{accion}", json=cuerpo)

    assert respuesta.status_code == HTTPStatus.BAD_REQUEST
    assert respuesta.json()["errorCode"] == "VALIDATION_FAILED"
    assert respuesta.json()["details"]
    assert lector.llamadas == []


async def test_una_accion_que_el_estado_no_permite_responde_403() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post(f"{RUTA}/tomar")

    assert respuesta.status_code == HTTPStatus.FORBIDDEN
    assert respuesta.json()["message"] == "No puedes tomar este caso en gestión."


async def test_un_caso_inexistente_responde_404() -> None:
    async with _cliente(IncidenciasEnMemoria()) as cliente:
        respuesta = await cliente.post(f"{RUTA}/confirmar")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()["message"] == "El caso solicitado no existe."


async def test_un_codigo_con_forma_invalida_responde_404() -> None:
    async with _cliente() as cliente:
        respuesta = await cliente.post("/v1/incidencias/no-es-un-codigo/confirmar")

    assert respuesta.status_code == HTTPStatus.NOT_FOUND


async def test_sin_la_vista_de_casos_responde_403() -> None:
    async with _cliente(sesion=una_sesion(roles=())) as cliente:
        respuesta = await cliente.post(f"{RUTA}/confirmar")

    assert respuesta.status_code == HTTPStatus.FORBIDDEN


async def test_sin_sesion_responde_401() -> None:
    async with _cliente(con_sesion=False) as cliente:
        respuesta = await cliente.post(f"{RUTA}/confirmar")

    assert respuesta.status_code == HTTPStatus.UNAUTHORIZED
