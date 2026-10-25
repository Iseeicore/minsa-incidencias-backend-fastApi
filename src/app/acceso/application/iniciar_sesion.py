from typing import TYPE_CHECKING

from app.constants.sesion import FAKE_PASSWORD
from app.errors.credenciales_invalidas import CredencialesInvalidas
from app.shared.actor import actor_usuario_interno

if TYPE_CHECKING:
    from app.acceso.application.ports import SesionStore, UsuarioFinder
    from app.shared.ports import PasswordHasher


def normalizar_correo(correo: str) -> str:
    return correo.strip().lower()


class IniciarSesion:
    def __init__(
        self, usuarios: UsuarioFinder, sesiones: SesionStore, hasher: PasswordHasher, horas_absolutas: int
    ) -> None:
        self._usuarios = usuarios
        self._sesiones = sesiones
        self._hasher = hasher
        self._horas_absolutas = horas_absolutas
        self._huella_falsa: str | None = None

    async def execute(self, correo: str, password: str) -> str:
        usuario = await self._usuarios.buscar_por_correo(normalizar_correo(correo))
        huella = usuario.password_hash if usuario is not None else await self._obtener_huella_falsa()
        coincide = await self._hasher.verify(huella, password)
        if usuario is None or not usuario.activo or not coincide:
            raise CredencialesInvalidas
        return await self._sesiones.crear(actor_usuario_interno(usuario.correo), usuario.id, self._horas_absolutas)

    async def _obtener_huella_falsa(self) -> str:
        if self._huella_falsa is None:
            self._huella_falsa = await self._hasher.hash(FAKE_PASSWORD)
        return self._huella_falsa
