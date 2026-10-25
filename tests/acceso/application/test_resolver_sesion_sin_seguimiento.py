import pytest

from app.acceso.application.resolver_sesion import ResolverSesion
from app.acceso.domain.sesion_vigente import SesionVigente
from app.errors.database_unavailable import DatabaseUnavailable
from tests.helpers.acceso_en_memoria import SesionesDeAccesoEnMemoria
from tests.helpers.builders import una_sesion_vigente


class _Rota(SesionesDeAccesoEnMemoria):
    async def buscar_vigente(
        self, sesion_id: str, minutos_inactividad: int, segundos_para_tocar: int
    ) -> SesionVigente | None:
        del sesion_id, minutos_inactividad, segundos_para_tocar
        raise DatabaseUnavailable


async def test_sin_seguimiento_un_error_de_la_base_sigue_su_camino() -> None:
    with pytest.raises(DatabaseUnavailable):
        await ResolverSesion(_Rota(), 30).resolve("cualquiera")


async def test_sin_seguimiento_una_sesion_resuelta_no_lleva_control() -> None:
    vigente = una_sesion_vigente()

    sesion = await ResolverSesion(SesionesDeAccesoEnMemoria({vigente.sesion_id: vigente}), 30).resolve(
        vigente.sesion_id
    )

    assert sesion is not None
    assert sesion.control_eventos is None
