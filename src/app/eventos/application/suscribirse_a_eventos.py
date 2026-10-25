from typing import TYPE_CHECKING

from app.errors.sesion_invalida import SesionInvalida
from app.shared.sesion import SesionEnVivo

if TYPE_CHECKING:
    from app.eventos.domain.centro_de_eventos import CentroDeEventos
    from app.eventos.domain.ports import DarDeBaja, Suscriptor
    from app.shared.sesion import SesionActual


class SuscribirseAEventos:
    def __init__(self, centro: CentroDeEventos) -> None:
        self._centro = centro

    def execute(self, sesion: SesionActual, suscriptor: Suscriptor) -> DarDeBaja:
        vigencia = sesion.vigencia
        control = sesion.control_eventos
        if vigencia is None or control is None or not control.vigente():
            raise SesionInvalida
        if vigencia.vence_en.tzinfo is None or vigencia.inactiva_en.tzinfo is None:
            raise SesionInvalida
        return self._centro.suscribir(
            SesionEnVivo(
                sesion_id=sesion.sesion_id,
                usuario_id=sesion.usuario_id,
                roles=sesion.roles,
                area_id=sesion.area.id if sesion.area is not None else None,
                vigencia=vigencia,
                control=control,
            ),
            suscriptor,
        )
