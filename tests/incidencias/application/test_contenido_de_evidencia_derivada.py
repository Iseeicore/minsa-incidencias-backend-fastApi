import pytest

from app.errors.no_encontrado import NoEncontrado
from app.incidencias.application.contenido_de_evidencia import ContenidoDeEvidencia
from app.incidencias.application.contenido_de_evidencia_derivada import ContenidoDeEvidenciaDerivada
from app.incidencias.application.visibilidad import VISIBILIDAD_DE_DERIVACIONES
from tests.helpers.builders import un_caso_consultado, una_sesion
from tests.helpers.casos import IMAGEN_PNG
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

ADMIN = una_sesion(roles=("ADMINISTRADOR",))
CODIGO = "MINSA-2026-000001"


async def test_entrega_la_imagen_leyendo_el_caso_con_la_visibilidad_del_seguimiento() -> None:
    lector = IncidenciasEnMemoria([un_caso_consultado()], rutas={"e1": IMAGEN_PNG})

    imagen = await ContenidoDeEvidenciaDerivada(ContenidoDeEvidencia(lector)).execute(ADMIN, CODIGO, "e1")

    assert imagen.tipo == "image/png"
    assert ("buscar_por_codigo", (CODIGO, VISIBILIDAD_DE_DERIVACIONES)) in lector.llamadas


async def test_un_caso_fuera_del_alcance_del_seguimiento_responde_404() -> None:
    contenido = ContenidoDeEvidenciaDerivada(ContenidoDeEvidencia(IncidenciasEnMemoria()))

    with pytest.raises(NoEncontrado, match=r"El caso solicitado no existe\."):
        await contenido.execute(ADMIN, CODIGO, "e1")
