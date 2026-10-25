import pytest

from app.incidencias.domain.cubos_de_evolucion import CuboDeEvolucion, DiaDeEvolucion, agrupar_en_cubos


def _dias(cantidad: int) -> list[DiaDeEvolucion]:
    return [DiaDeEvolucion(f"2026-01-{indice:02d}", indice, indice * 10) for indice in range(1, cantidad + 1)]


def test_con_un_dia_por_cubo_cada_dia_es_su_propio_cubo() -> None:
    cubos = agrupar_en_cubos(_dias(3), 1)

    assert cubos == [
        CuboDeEvolucion("2026-01-01", 1, 10),
        CuboDeEvolucion("2026-01-02", 2, 20),
        CuboDeEvolucion("2026-01-03", 3, 30),
    ]


def test_cada_cubo_suma_sus_dias_y_empieza_en_el_primero() -> None:
    cubos = agrupar_en_cubos(_dias(5), 2)

    assert cubos == [
        CuboDeEvolucion("2026-01-01", 3, 30),
        CuboDeEvolucion("2026-01-03", 7, 70),
        CuboDeEvolucion("2026-01-05", 5, 50),
    ]


def test_una_semana_completa_cabe_en_un_solo_cubo() -> None:
    [cubo] = agrupar_en_cubos(_dias(7), 7)

    assert (cubo.desde, cubo.recibidos, cubo.resueltos) == ("2026-01-01", 28, 280)


@pytest.mark.parametrize("dias_por_cubo", [0, -3])
def test_un_paso_menor_que_uno_se_trata_como_un_dia(dias_por_cubo: int) -> None:
    assert len(agrupar_en_cubos(_dias(4), dias_por_cubo)) == 4


def test_sin_dias_no_hay_cubos() -> None:
    assert agrupar_en_cubos([], 7) == []
