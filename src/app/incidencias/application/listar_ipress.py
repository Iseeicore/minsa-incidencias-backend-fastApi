from typing import TYPE_CHECKING

from app.shared.cursor import PosicionPorNombre, encode_int_cursor
from app.shared.pagination import limite_con_extra, pagina_de

if TYPE_CHECKING:
    from app.incidencias.application.ports import IpressFinder
    from app.incidencias.domain.ipress import ConsultaDeIpress, IpressListada
    from app.shared.pagination import Pagina


def _cursor_de(ipress: IpressListada) -> str:
    return encode_int_cursor(PosicionPorNombre(ipress.nombre, ipress.id))


class ListarIpress:
    def __init__(self, ipress: IpressFinder) -> None:
        self._ipress = ipress

    async def execute(self, consulta: ConsultaDeIpress) -> Pagina[IpressListada]:
        filas = await self._ipress.listar(consulta, limite_con_extra(consulta.limite))
        return pagina_de(filas, consulta.limite, _cursor_de)
