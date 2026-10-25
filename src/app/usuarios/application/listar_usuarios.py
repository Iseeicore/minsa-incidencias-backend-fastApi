from typing import TYPE_CHECKING

from app.shared.cursor import PosicionPorNombre, encode_uuid_cursor
from app.shared.pagination import limite_con_extra, pagina_de
from app.usuarios.domain.gestion import exigir_gestion, restriccion_de
from app.usuarios.domain.pedidos import FiltrosDeUsuarios

if TYPE_CHECKING:
    from app.shared.pagination import Pagina
    from app.shared.sesion import SesionActual
    from app.usuarios.application.ports import UsuarioReader
    from app.usuarios.domain.pedidos import ConsultaUsuarios
    from app.usuarios.domain.usuario_gestionado import UsuarioGestionado


def _cursor_de(usuario: UsuarioGestionado) -> str:
    return encode_uuid_cursor(PosicionPorNombre(usuario.nombre_completo, usuario.id))


class ListarUsuarios:
    def __init__(self, usuarios: UsuarioReader) -> None:
        self._usuarios = usuarios

    async def execute(self, sesion: SesionActual, consulta: ConsultaUsuarios) -> Pagina[UsuarioGestionado]:
        gestion = exigir_gestion(sesion.roles)
        restriccion = restriccion_de(sesion, gestion)
        filtros = FiltrosDeUsuarios(
            texto=consulta.texto,
            area_codigo=None if restriccion is not None else consulta.area,
            restriccion_de_area=restriccion,
        )
        filas = await self._usuarios.listar(filtros, limite_con_extra(consulta.limite), consulta.despues_de)
        return pagina_de(filas, consulta.limite, _cursor_de)
