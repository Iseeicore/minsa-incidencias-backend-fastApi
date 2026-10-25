import pytest

from app.nota.application.crear_nota import CrearNota, CrearNotaComando
from app.nota.domain.errors.titulo_invalido import TituloInvalido
from tests.helpers.builders import un_codigo
from tests.helpers.fakes import AHORA_FIJA, FixedClock, InMemoryNotaRepository, SequentialCodeGenerator


def un_caso_de_uso(repositorio: InMemoryNotaRepository) -> CrearNota:
    return CrearNota(repositorio, SequentialCodeGenerator(), FixedClock())


async def test_crea_la_nota_con_el_siguiente_codigo_y_la_hora_del_reloj() -> None:
    repositorio = InMemoryNotaRepository()

    nota = await un_caso_de_uso(repositorio).execute(CrearNotaComando(titulo="Titulo", contenido="Contenido"))

    assert nota.codigo.valor == "NOTA-000001"
    assert nota.creada_en == AHORA_FIJA


async def test_deja_la_nota_guardada_en_el_repositorio() -> None:
    repositorio = InMemoryNotaRepository()

    nota = await un_caso_de_uso(repositorio).execute(CrearNotaComando(titulo="Titulo", contenido="Contenido"))

    assert await repositorio.find_by_codigo(nota.codigo) == nota


async def test_no_guarda_nada_si_el_titulo_es_invalido() -> None:
    repositorio = InMemoryNotaRepository()

    with pytest.raises(TituloInvalido):
        await un_caso_de_uso(repositorio).execute(CrearNotaComando(titulo=" ", contenido="Contenido"))

    assert await repositorio.find_by_codigo(un_codigo()) is None
