from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.acceso.domain.sesion_vigente import SesionVigente
    from app.acceso.domain.usuario_interno import UsuarioInterno
    from app.shared.sesion import VigenciaDeSesion


class UsuarioFinder(Protocol):
    async def buscar_por_correo(self, correo: str) -> UsuarioInterno | None: ...


class SesionStore(Protocol):
    async def crear(self, actor: str, usuario_id: str, horas_absolutas: int) -> str: ...

    async def buscar_vigente(
        self, sesion_id: str, minutos_inactividad: int, segundos_para_tocar: int
    ) -> SesionVigente | None: ...

    async def tocar_actividad(
        self, actor: str, sesion_id: str, minutos_inactividad: int
    ) -> VigenciaDeSesion | None: ...

    async def revocar(self, actor: str, sesion_id: str) -> None: ...

    async def buscar_correo_de_sesion_abierta(self, sesion_id: str) -> str | None: ...
