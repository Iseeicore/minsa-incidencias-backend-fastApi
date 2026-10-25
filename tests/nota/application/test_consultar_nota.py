import pytest

from app.nota.application.consultar_nota import ConsultarNota
from app.nota.domain.errors.codigo_nota_invalido import CodigoNotaInvalido
from app.nota.domain.errors.nota_no_encontrada import NotaNoEncontrada
from tests.helpers.builders import una_nota
from tests.helpers.fakes import InMemoryNotaRepository


async def test_devuelve_la_nota_que_existe() -> None:
    nota = una_nota(7)

    assert await ConsultarNota(InMemoryNotaRepository([nota])).execute("NOTA-000007") == nota


async def test_falla_si_la_nota_no_existe() -> None:
    with pytest.raises(NotaNoEncontrada):
        await ConsultarNota(InMemoryNotaRepository()).execute("NOTA-000099")


async def test_falla_si_el_codigo_tiene_otro_formato() -> None:
    with pytest.raises(CodigoNotaInvalido):
        await ConsultarNota(InMemoryNotaRepository()).execute("otro")
