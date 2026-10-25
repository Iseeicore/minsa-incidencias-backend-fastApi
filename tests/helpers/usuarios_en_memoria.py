from contextlib import asynccontextmanager
from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import uuid4

from app.errors.correo_repetido import CorreoRepetido
from app.usuarios.domain.usuario_gestionado import UsuarioGestionado

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.enums.rol_codigo import RolCodigo
    from app.shared.cursor import PosicionPorNombre
    from app.usuarios.domain.pedidos import FiltrosDeUsuarios, NuevoUsuarioFila, RestriccionDeArea

AREAS_DE_PRUEBA = {
    "HOSP-01": (1, "Hospital Uno"),
    "HOSP-02": (2, "Hospital Dos"),
    "OTRANS": (3, "Oficina de Transparencia"),
}


class UsuariosEnMemoria:
    def __init__(self, usuarios: list[UsuarioGestionado] | None = None) -> None:
        self.usuarios: dict[str, UsuarioGestionado] = {usuario.id: usuario for usuario in usuarios or []}
        self.huellas: dict[str, str] = {}
        self.actores: list[str] = []
        self.sesiones_cerradas: list[str] = []
        self.areas_inactivas: set[str] = set()

    async def listar(
        self, filtros: FiltrosDeUsuarios, limite: int, despues_de: PosicionPorNombre[str] | None
    ) -> list[UsuarioGestionado]:
        filas = sorted(self.usuarios.values(), key=lambda usuario: (usuario.nombre_completo, usuario.id))
        if filtros.restriccion_de_area is not None:
            filas = [fila for fila in filas if fila.area_id == filtros.restriccion_de_area.area_id]
        if filtros.area_codigo:
            filas = [fila for fila in filas if fila.area_codigo == filtros.area_codigo]
        if filtros.texto:
            texto = filtros.texto.lower()
            filas = [fila for fila in filas if texto in fila.nombre_completo.lower() or texto in fila.correo]
        if despues_de is not None:
            filas = [fila for fila in filas if (fila.nombre_completo, fila.id) > (despues_de.nombre, despues_de.id)]
        return filas[:limite]

    @asynccontextmanager
    async def begin(self, actor: str) -> AsyncIterator[TransaccionEnMemoria]:
        respaldo = (dict(self.usuarios), dict(self.huellas), list(self.sesiones_cerradas))
        self.actores.append(actor)
        try:
            yield TransaccionEnMemoria(self)
        except BaseException:
            self.usuarios, self.huellas, self.sesiones_cerradas = respaldo
            raise


class TransaccionEnMemoria:
    def __init__(self, almacen: UsuariosEnMemoria) -> None:
        self._almacen = almacen

    async def buscar_por_id(
        self,
        usuario_id: str,
        restriccion: RestriccionDeArea | None,
        *,
        bloquear: bool = False,  # noqa: ARG002
    ) -> UsuarioGestionado | None:
        usuario = self._almacen.usuarios.get(usuario_id)
        if usuario is None:
            return None
        if restriccion is not None and usuario.area_id != restriccion.area_id:
            return None
        return usuario

    async def area_activa(self, codigo: str) -> int | None:
        if codigo in self._almacen.areas_inactivas or codigo not in AREAS_DE_PRUEBA:
            return None
        return AREAS_DE_PRUEBA[codigo][0]

    async def crear(self, datos: NuevoUsuarioFila) -> str:
        if any(usuario.correo == datos.correo for usuario in self._almacen.usuarios.values()):
            raise CorreoRepetido
        nuevo_id = str(uuid4())
        area = next(
            ((codigo, nombre) for codigo, (area_id, nombre) in AREAS_DE_PRUEBA.items() if area_id == datos.area_id),
            None,
        )
        self._almacen.usuarios[nuevo_id] = UsuarioGestionado(
            id=nuevo_id,
            nombre_completo=datos.nombre_completo,
            correo=datos.correo,
            activo=True,
            rol=None,
            area_id=datos.area_id,
            area_codigo=area[0] if area else None,
            area_nombre=area[1] if area else None,
        )
        self._almacen.huellas[nuevo_id] = datos.huella
        return nuevo_id

    async def asignar_rol(self, usuario_id: str, rol: RolCodigo) -> None:
        self._almacen.usuarios[usuario_id] = replace(self._almacen.usuarios[usuario_id], rol=rol.value)

    async def quitar_roles(self, usuario_id: str) -> None:
        self._almacen.usuarios[usuario_id] = replace(self._almacen.usuarios[usuario_id], rol=None)

    async def cambiar_area(self, usuario_id: str, area_id: int | None) -> None:
        area = next(((codigo, nombre) for codigo, (id_, nombre) in AREAS_DE_PRUEBA.items() if id_ == area_id), None)
        self._almacen.usuarios[usuario_id] = replace(
            self._almacen.usuarios[usuario_id],
            area_id=area_id,
            area_codigo=area[0] if area else None,
            area_nombre=area[1] if area else None,
        )

    async def cambiar_nombre(self, usuario_id: str, nombre_completo: str) -> None:
        self._almacen.usuarios[usuario_id] = replace(
            self._almacen.usuarios[usuario_id], nombre_completo=nombre_completo
        )

    async def cambiar_vigencia(self, usuario_id: str, *, activo: bool, actor: str) -> None:  # noqa: ARG002
        self._almacen.usuarios[usuario_id] = replace(self._almacen.usuarios[usuario_id], activo=activo)

    async def cambiar_clave(self, usuario_id: str, huella: str) -> None:
        self._almacen.huellas[usuario_id] = huella

    async def cerrar_sesiones(self, usuario_id: str) -> None:
        self._almacen.sesiones_cerradas.append(usuario_id)
