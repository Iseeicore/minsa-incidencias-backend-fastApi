from app.constants.eventos import EVENTOS_AGRUPADO_SEGUNDOS, EVENTOS_CATEGORIAS_CACHE_SEGUNDOS
from app.constants.textos.eventos import EVENTO_CATEGORIAS_NO_LEIDAS
from app.enums.evento_nombre import EventoNombre
from app.enums.rol_codigo import RolCodigo
from app.eventos.application.publicar_cambios import PublicarCambios
from app.eventos.domain.cambio_de_incidencia import CambioDeIncidencia
from app.eventos.domain.centro_de_eventos import CentroDeEventos
from tests.helpers.eventos_en_memoria import (
    CORRUPCION,
    QUEJA,
    CategoriasEnMemoria,
    SuscriptorFalso,
    TiempoManual,
    una_sesion_en_vivo,
)
from tests.helpers.registro_en_memoria import RegistroEnMemoria

AREA_OTRANS = 10
AREA_A = 21


class Escenario:
    def __init__(self) -> None:
        self.tiempo = TiempoManual()
        self.registro = RegistroEnMemoria()
        self.categorias = CategoriasEnMemoria()
        self.centro = CentroDeEventos(self.tiempo, self.registro)
        self.publicar = PublicarCambios(self.centro, self.categorias, self.tiempo, self.registro)

    def conectar(self, rol: str, area_id: int | None, usuario: str) -> SuscriptorFalso:
        suscriptor = SuscriptorFalso()
        self.centro.suscribir(una_sesion_en_vivo(rol, area_id, usuario_id=usuario, sesion_id=usuario), suscriptor)
        return suscriptor


def en_area(area: int, categoria: int) -> CambioDeIncidencia:
    return CambioDeIncidencia(area, area, categoria, categoria)


async def test_sin_conectados_no_lee_las_categorias() -> None:
    escenario = Escenario()

    await escenario.publicar.execute([en_area(AREA_A, QUEJA)])

    assert escenario.categorias.llamadas == 0


async def test_sin_cambios_no_lee_las_categorias() -> None:
    escenario = Escenario()
    escenario.conectar(RolCodigo.GESTOR, AREA_A, "uno")

    await escenario.publicar.execute([])

    assert escenario.categorias.llamadas == 0


async def test_un_cambio_dirigido_llega_solo_a_quien_corresponde() -> None:
    escenario = Escenario()
    establecimiento = escenario.conectar(RolCodigo.ESTABLECIMIENTO, AREA_A, "uno")
    otrans = escenario.conectar(RolCodigo.OTRANS, AREA_OTRANS, "dos")

    await escenario.publicar.execute([en_area(AREA_OTRANS, CORRUPCION)])
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)

    assert otrans.enviados == [EventoNombre.CAMBIO]
    assert establecimiento.enviados == []


async def test_las_categorias_se_guardan_cinco_minutos_y_luego_se_vuelven_a_leer() -> None:
    escenario = Escenario()
    escenario.conectar(RolCodigo.GESTOR, AREA_A, "uno")

    await escenario.publicar.execute([en_area(AREA_A, QUEJA)])
    await escenario.publicar.execute([en_area(AREA_A, QUEJA)])
    assert escenario.categorias.llamadas == 1
    escenario.tiempo.avanzar(EVENTOS_CATEGORIAS_CACHE_SEGUNDOS - 1)
    await escenario.publicar.execute([en_area(AREA_A, QUEJA)])
    assert escenario.categorias.llamadas == 1
    escenario.tiempo.avanzar(1)
    await escenario.publicar.execute([en_area(AREA_A, QUEJA)])

    assert escenario.categorias.llamadas == 2


async def test_si_no_se_pueden_leer_las_categorias_avisa_no_publica_y_reintenta_despues() -> None:
    escenario = Escenario()
    cliente = escenario.conectar(RolCodigo.GESTOR, AREA_A, "uno")
    escenario.categorias.falla = RuntimeError("sin base")

    await escenario.publicar.execute([en_area(AREA_A, QUEJA)])
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)

    assert cliente.enviados == []
    assert escenario.registro.eventos[-1] == ("warning", EVENTO_CATEGORIAS_NO_LEIDAS, {"error": "RuntimeError"})
    escenario.categorias.falla = None
    await escenario.publicar.execute([en_area(AREA_A, QUEJA)])
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)
    assert (escenario.categorias.llamadas, cliente.enviados) == (2, [EventoNombre.CAMBIO])


def test_publicar_un_cambio_general_avisa_a_todos_sin_leer_categorias() -> None:
    escenario = Escenario()
    cliente = escenario.conectar(RolCodigo.GESTOR, AREA_A, "uno")

    escenario.publicar.publicar_cambio()
    escenario.tiempo.avanzar(EVENTOS_AGRUPADO_SEGUNDOS)

    assert cliente.enviados == [EventoNombre.CAMBIO]
    assert escenario.categorias.llamadas == 0
