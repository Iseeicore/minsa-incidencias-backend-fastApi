import asyncio

from app.archivador.application.archivar_incidencias import ArchivarIncidencias
from app.archivador.domain.resultado_de_archivado import ResultadoDeArchivado
from app.constants.textos.procesos import EVENTO_ARCHIVADO_COMPLETADO, EVENTO_FALLO_EL_ARCHIVADO
from tests.helpers.registro_en_memoria import RegistroEnMemoria


class _ErrorSinBase(Exception):
    pass


class _Repositorio:
    def __init__(self, vencidas: int = 0, resueltas: int = 0, *, falla: bool = False) -> None:
        self.vencidas = vencidas
        self.resueltas = resueltas
        self.falla = falla
        self.llamadas: list[tuple[str, tuple[int, ...]]] = []
        self.pausa: asyncio.Event | None = None

    async def archivar_vencidas(self, lote: int) -> int:
        self.llamadas.append(("vencidas", (lote,)))
        if self.pausa is not None:
            await self.pausa.wait()
        if self.falla:
            raise _ErrorSinBase
        return self.vencidas

    async def archivar_resueltas(self, dias: int, lote: int) -> int:
        self.llamadas.append(("resueltas", (dias, lote)))
        return self.resueltas


def _archivador(repositorio: _Repositorio, registro: RegistroEnMemoria) -> ArchivarIncidencias:
    return ArchivarIncidencias(repositorio, registro, vigencia_dias=3, lote=1000)


async def test_archiva_primero_las_vencidas_y_luego_las_resueltas_con_la_vigencia_y_el_lote() -> None:
    repositorio = _Repositorio(vencidas=2, resueltas=5)

    resultado = await _archivador(repositorio, RegistroEnMemoria()).ejecutar()

    assert resultado == ResultadoDeArchivado(2, 5)
    assert repositorio.llamadas == [("vencidas", (1000,)), ("resueltas", (3, 1000))]


async def test_una_ejecucion_en_curso_hace_que_la_siguiente_no_haga_nada() -> None:
    repositorio = _Repositorio(vencidas=1)
    repositorio.pausa = asyncio.Event()
    archivador = _archivador(repositorio, RegistroEnMemoria())
    primera = asyncio.create_task(archivador.ejecutar())
    await asyncio.sleep(0.02)

    segunda = await archivador.ejecutar()
    repositorio.pausa.set()

    assert segunda == ResultadoDeArchivado()
    assert (await primera).abiertas == 1
    assert len(repositorio.llamadas) == 2


async def test_despues_de_terminar_o_fallar_se_puede_volver_a_ejecutar() -> None:
    repositorio = _Repositorio(vencidas=1, falla=True)
    archivador = _archivador(repositorio, RegistroEnMemoria())

    await archivador.ejecutar_con_registro()
    repositorio.falla = False

    assert (await archivador.ejecutar()).abiertas == 1


async def test_con_registro_informa_solo_cuando_archivo_algo() -> None:
    registro = RegistroEnMemoria()

    await _archivador(_Repositorio(), registro).ejecutar_con_registro()
    await _archivador(_Repositorio(vencidas=1, resueltas=2), registro).ejecutar_con_registro()

    assert registro.eventos == [("info", EVENTO_ARCHIVADO_COMPLETADO, {"abiertas": 1, "resueltas": 2})]


async def test_si_el_archivado_falla_lo_registra_sin_propagar_el_error() -> None:
    registro = RegistroEnMemoria()

    await _archivador(_Repositorio(falla=True), registro).ejecutar_con_registro()

    assert registro.eventos == [("error", EVENTO_FALLO_EL_ARCHIVADO, {"error": "_ErrorSinBase"})]
