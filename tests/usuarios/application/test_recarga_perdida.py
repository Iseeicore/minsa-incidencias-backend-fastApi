from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import pytest

from app.enums.rol_codigo import RolCodigo
from app.errors.no_encontrado import NoEncontrado
from app.usuarios.application.actualizar_usuario import ActualizarUsuario
from app.usuarios.application.crear_usuario import CrearUsuario
from app.usuarios.domain.pedidos import CambiosDeUsuario, DatosNuevoUsuario
from tests.helpers.acceso_en_memoria import HasherFalso
from tests.helpers.builders import un_usuario_gestionado, una_sesion
from tests.helpers.usuarios_en_memoria import TransaccionEnMemoria, UsuariosEnMemoria

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.usuarios.domain.pedidos import RestriccionDeArea
    from app.usuarios.domain.usuario_gestionado import UsuarioGestionado

ANA = "11111111-1111-4111-8111-111111111111"
ADMIN = una_sesion(correo="admin@minsa.gob.pe", roles=("ADMINISTRADOR",))


class TransaccionQuePierdeAlRecargar(TransaccionEnMemoria):
    async def buscar_por_id(
        self, usuario_id: str, restriccion: RestriccionDeArea | None, *, bloquear: bool = False
    ) -> UsuarioGestionado | None:
        if restriccion is None and not bloquear:
            return None
        return await super().buscar_por_id(usuario_id, restriccion, bloquear=bloquear)


class AlmacenQuePierdeAlRecargar(UsuariosEnMemoria):
    @asynccontextmanager
    async def begin(self, actor: str) -> AsyncIterator[TransaccionEnMemoria]:
        async with super().begin(actor):
            yield TransaccionQuePierdeAlRecargar(self)


async def test_si_el_usuario_creado_ya_no_se_puede_leer_responde_404() -> None:
    caso = CrearUsuario(AlmacenQuePierdeAlRecargar(), HasherFalso())

    with pytest.raises(NoEncontrado):
        await caso.execute(ADMIN, DatosNuevoUsuario("Dora", "dora@minsa.gob.pe", RolCodigo.GESTOR, "HOSP-01"))


async def test_si_el_usuario_actualizado_ya_no_se_puede_leer_responde_404() -> None:
    almacen = AlmacenQuePierdeAlRecargar([un_usuario_gestionado(ANA)])

    with pytest.raises(NoEncontrado):
        await ActualizarUsuario(almacen).execute(ADMIN, ANA, CambiosDeUsuario(nombre_completo="Ana Nueva"))
