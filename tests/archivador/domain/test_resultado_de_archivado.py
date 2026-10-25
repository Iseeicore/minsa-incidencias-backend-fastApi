import pytest

from app.archivador.domain.resultado_de_archivado import ResultadoDeArchivado


def test_el_resultado_vacio_no_tiene_cambios() -> None:
    resultado = ResultadoDeArchivado()

    assert (resultado.abiertas, resultado.resueltas, resultado.hubo_cambios) == (0, 0, False)


@pytest.mark.parametrize(("abiertas", "resueltas"), [(1, 0), (0, 2), (3, 4)])
def test_hay_cambios_si_se_archivo_algun_caso_de_cualquier_tipo(abiertas: int, resueltas: int) -> None:
    assert ResultadoDeArchivado(abiertas, resueltas).hubo_cambios is True
