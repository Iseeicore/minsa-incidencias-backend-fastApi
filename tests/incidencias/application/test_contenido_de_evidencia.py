import pytest

from app.errors.evidencia_no_disponible import EvidenciaNoDisponible
from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.contenido_de_evidencia import ContenidoDeEvidencia
from tests.helpers.builders import un_caso_consultado, una_sesion
from tests.helpers.casos import IMAGEN_PNG
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

ADMIN = una_sesion(roles=("ADMINISTRADOR",))
CODIGO = "MINSA-2026-000001"


async def test_entrega_la_imagen_guardada_como_data_uri() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()], rutas={"e1": IMAGEN_PNG})

    imagen = await ContenidoDeEvidencia(lector).execute(ADMIN, CODIGO, "e1")

    assert imagen.tipo == "image/png"
    assert imagen.contenido.startswith(b"\x89PNG")


async def test_un_caso_que_no_se_ve_responde_404_con_el_mensaje_del_caso() -> None:
    with pytest.raises(NoEncontrado, match=r"El caso solicitado no existe\."):
        await ContenidoDeEvidencia(IncidenciasEnMemoria()).execute(ADMIN, CODIGO, "e1")


async def test_una_evidencia_ajena_o_inexistente_responde_404_con_su_mensaje() -> None:
    with pytest.raises(NoEncontrado, match=r"La evidencia solicitada no existe\."):
        await ContenidoDeEvidencia(IncidenciasEnMemoria([un_caso_consultado()])).execute(ADMIN, CODIGO, "e1")


@pytest.mark.parametrize(
    "ruta", ["rutas-privadas/archivo.jpg", "data:image/gif;base64,AAAA", "data:image/png;base64,@@@@"]
)
async def test_lo_que_no_es_una_imagen_permitida_responde_evidencia_no_disponible(ruta: str) -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()], rutas={"e1": ruta})

    with pytest.raises(EvidenciaNoDisponible):
        await ContenidoDeEvidencia(lector).execute(ADMIN, CODIGO, "e1")
