from datetime import UTC, datetime

from app.incidencias.application.listar_derivaciones import ListarDerivaciones
from app.incidencias.domain.cursores import PosicionDeDerivacion, decodificar_cursor_de_derivacion
from app.incidencias.domain.derivaciones import ConsultaDeDerivaciones, DerivacionConsultada
from tests.helpers.builders import una_derivacion_consultada
from tests.helpers.derivaciones_en_memoria import DerivacionesEnMemoria

MARCA = datetime(2026, 10, 24, 9, 30, 15, 123_456, tzinfo=UTC)


def _derivaciones(cantidad: int) -> list[DerivacionConsultada]:
    return [
        una_derivacion_consultada(id=str(4800 + indice), codigo_caso=f"MINSA-2026-{indice:06d}", fecha_derivacion=MARCA)
        for indice in range(1, cantidad + 1)
    ]


async def test_pide_una_fila_de_mas_y_arma_el_cursor_del_ultimo_cuando_hay_mas() -> None:
    lector = DerivacionesEnMemoria(_derivaciones(3))

    pagina = await ListarDerivaciones(lector).execute(ConsultaDeDerivaciones(limite=2))

    assert [item.codigo_caso for item in pagina.items] == ["MINSA-2026-000001", "MINSA-2026-000002"]
    assert pagina.hay_mas is True
    assert decodificar_cursor_de_derivacion(pagina.siguiente or "") == PosicionDeDerivacion(
        MARCA.replace(microsecond=123_000), "4802"
    )
    assert lector.consultas[0][1] == 3


async def test_sin_mas_filas_no_hay_cursor() -> None:
    pagina = await ListarDerivaciones(DerivacionesEnMemoria(_derivaciones(2))).execute(ConsultaDeDerivaciones(limite=2))

    assert (pagina.siguiente, pagina.hay_mas, len(pagina.items)) == (None, False, 2)


async def test_pasa_la_consulta_completa_al_lector() -> None:
    lector = DerivacionesEnMemoria()
    consulta = ConsultaDeDerivaciones(limite=5, despues_de=PosicionDeDerivacion(MARCA, "9"))

    await ListarDerivaciones(lector).execute(consulta)

    assert lector.consultas == [(consulta, 6)]
