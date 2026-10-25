from typing import TYPE_CHECKING

from app.incidencias.application.visibilidad import VISIBILIDAD_DE_DERIVACIONES

if TYPE_CHECKING:
    from app.incidencias.application.contenido_de_evidencia import ContenidoDeEvidencia
    from app.incidencias.domain.imagen_de_evidencia import ImagenDeEvidencia
    from app.shared.sesion import SesionActual


class ContenidoDeEvidenciaDerivada:
    def __init__(self, contenido: ContenidoDeEvidencia) -> None:
        self._contenido = contenido

    async def execute(self, sesion: SesionActual, codigo: str, evidencia_id: str) -> ImagenDeEvidencia:
        return await self._contenido.execute(sesion, codigo, evidencia_id, VISIBILIDAD_DE_DERIVACIONES)
