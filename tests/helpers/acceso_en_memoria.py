from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from app.acceso.domain.sesion_vigente import SesionVigente
    from app.acceso.domain.usuario_interno import UsuarioInterno
    from app.catalogos.domain.area_listada import AreaListada, FiltrosDeAreas
    from app.shared.cursor import PosicionPorNombre
    from app.shared.sesion import VigenciaDeSesion


class HasherFalso:
    def __init__(self) -> None:
        self.hashes: list[str] = []
        self.verificaciones: list[tuple[str, str]] = []

    async def hash(self, plain: str) -> str:
        self.hashes.append(plain)
        return f"hash:{plain}"

    async def verify(self, hashed: str, plain: str) -> bool:
        self.verificaciones.append((hashed, plain))
        return hashed == f"hash:{plain}"


class UsuariosDeAccesoEnMemoria:
    def __init__(self, usuarios: list[UsuarioInterno] | None = None) -> None:
        self._usuarios = {usuario.correo: usuario for usuario in usuarios or []}
        self.consultas: list[str] = []

    async def buscar_por_correo(self, correo: str) -> UsuarioInterno | None:
        self.consultas.append(correo)
        return self._usuarios.get(correo)


class SesionesDeAccesoEnMemoria:
    def __init__(self, vigentes: dict[str, SesionVigente] | None = None) -> None:
        self.vigentes = dict(vigentes or {})
        self.creadas: list[tuple[str, str, int]] = []
        self.revocadas: list[tuple[str, str]] = []
        self.tocadas: list[tuple[str, str, int]] = []
        self.falla_al_revocar: Exception | None = None
        self.vigencia_al_tocar: VigenciaDeSesion | None = None

    async def crear(self, actor: str, usuario_id: str, horas_absolutas: int) -> str:
        self.creadas.append((actor, usuario_id, horas_absolutas))
        return str(uuid4())

    async def buscar_vigente(
        self,
        sesion_id: str,
        minutos_inactividad: int,  # noqa: ARG002
        segundos_para_tocar: int,  # noqa: ARG002
    ) -> SesionVigente | None:
        return self.vigentes.get(sesion_id)

    async def tocar_actividad(self, actor: str, sesion_id: str, minutos_inactividad: int) -> VigenciaDeSesion | None:
        self.tocadas.append((actor, sesion_id, minutos_inactividad))
        return self.vigencia_al_tocar

    async def revocar(self, actor: str, sesion_id: str) -> None:
        if self.falla_al_revocar is not None:
            raise self.falla_al_revocar
        self.revocadas.append((actor, sesion_id))
        self.vigentes.pop(sesion_id, None)

    async def buscar_correo_de_sesion_abierta(self, sesion_id: str) -> str | None:
        vigente = self.vigentes.get(sesion_id)
        return vigente.correo if vigente is not None else None

    def con_debe_tocar(self, sesion_id: str, *, debe_tocar: bool) -> None:
        self.vigentes[sesion_id] = replace(self.vigentes[sesion_id], debe_tocar=debe_tocar)


class AreasEnMemoria:
    def __init__(self, areas: list[AreaListada] | None = None) -> None:
        self.areas = list(areas or [])
        self.consultas: list[tuple[FiltrosDeAreas, int, PosicionPorNombre[int] | None]] = []

    async def listar(
        self, filtros: FiltrosDeAreas, limite: int, despues_de: PosicionPorNombre[int] | None
    ) -> list[AreaListada]:
        self.consultas.append((filtros, limite, despues_de))
        return self.areas[:limite]
