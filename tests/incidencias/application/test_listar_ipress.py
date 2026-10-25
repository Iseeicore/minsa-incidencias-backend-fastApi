from app.incidencias.application.listar_ipress import ListarIpress
from app.incidencias.domain.ipress import ConsultaDeIpress, IpressListada
from app.shared.cursor import PosicionPorNombre, decode_int_cursor
from tests.helpers.indicadores_en_memoria import IpressEnMemoria


def _ipress(cantidad: int) -> list[IpressListada]:
    return [
        IpressListada(indice, f"EESS-{indice:04d}", f"Centro {indice}", str(indice), "I", "I-3")
        for indice in range(1, cantidad + 1)
    ]


async def test_pide_una_fila_de_mas_y_arma_el_cursor_por_nombre_del_ultimo() -> None:
    buscador = IpressEnMemoria(listadas=_ipress(3))

    pagina = await ListarIpress(buscador).execute(ConsultaDeIpress(limite=2))

    assert [ipress.id for ipress in pagina.items] == [1, 2]
    assert pagina.hay_mas is True
    assert decode_int_cursor(pagina.siguiente or "") == PosicionPorNombre("Centro 2", 2)
    assert buscador.consultas[0][1] == 3


async def test_sin_mas_filas_no_hay_cursor() -> None:
    pagina = await ListarIpress(IpressEnMemoria(listadas=_ipress(2))).execute(ConsultaDeIpress(limite=2))

    assert (pagina.siguiente, pagina.hay_mas, len(pagina.items)) == (None, False, 2)
