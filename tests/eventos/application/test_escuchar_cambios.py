import asyncio
import json
from typing import TYPE_CHECKING

import pytest

from app.constants.eventos import CANAL_CAMBIOS_INCIDENCIAS
from app.constants.textos.eventos import (
    EVENTO_CIERRE_FALLIDO,
    EVENTO_ESCUCHA_PERDIDA,
    EVENTO_ESCUCHANDO,
    EVENTO_NOTIFICACION_DESCARTADA,
)
from app.eventos.application.escuchar_cambios import EscucharCambios
from app.eventos.application.ports import NotificacionDeCanal
from app.eventos.domain.cambio_de_incidencia import CambioDeIncidencia
from tests.helpers.registro_en_memoria import RegistroEnMemoria

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Sequence

    from app.eventos.application.ports import ConexionDeNotificaciones

REINTENTO = 0.01
VALIDO = json.dumps({"areaAntes": None, "areaDespues": 10, "categoriaAntes": None, "categoriaDespues": 3})


class _PerdidaDelEnlace(Exception):
    pass


class ConexionFalsa:
    def __init__(self, avisos: Sequence[NotificacionDeCanal | Exception], *, quedarse_abierta: bool = False) -> None:
        self._avisos = avisos
        self._quedarse_abierta = quedarse_abierta
        self.cerrada = False
        self.falla_al_cerrar = False

    async def notificaciones(self) -> AsyncIterator[NotificacionDeCanal]:
        for aviso in self._avisos:
            if isinstance(aviso, Exception):
                raise aviso
            yield aviso
        if self._quedarse_abierta:
            await asyncio.Event().wait()

    async def cerrar(self) -> None:
        self.cerrada = True
        if self.falla_al_cerrar:
            raise _PerdidaDelEnlace


class AbridorFalso:
    def __init__(self, *conexiones: ConexionFalsa | Exception) -> None:
        self._pendientes = list(conexiones)
        self.aperturas = 0

    async def abrir(self) -> ConexionDeNotificaciones:
        self.aperturas += 1
        siguiente = self._pendientes.pop(0) if self._pendientes else ConexionFalsa([], quedarse_abierta=True)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


class InstaladorFalso:
    def __init__(self, *, falla: bool = False) -> None:
        self.instalaciones = 0
        self._falla = falla

    async def instalar(self) -> None:
        self.instalaciones += 1
        if self._falla:
            raise _PerdidaDelEnlace


class PublicarFalso:
    def __init__(self) -> None:
        self.publicados: list[list[CambioDeIncidencia]] = []
        self.generales = 0

    async def execute(self, cambios: list[CambioDeIncidencia]) -> None:
        self.publicados.append(list(cambios))

    def publicar_cambio(self) -> None:
        self.generales += 1


async def _esperar(condicion: Callable[[], bool]) -> None:
    async with asyncio.timeout(2):
        while not condicion():  # noqa: ASYNC110
            await asyncio.sleep(0.005)


def _escuchador(
    abridor: AbridorFalso, instalador: InstaladorFalso | None = None
) -> tuple[EscucharCambios, PublicarFalso, RegistroEnMemoria]:
    publicar = PublicarFalso()
    registro = RegistroEnMemoria()
    escuchador = EscucharCambios(instalador or InstaladorFalso(), abridor, publicar, registro, REINTENTO)  # type: ignore[arg-type]
    return escuchador, publicar, registro


async def test_instala_las_notificaciones_antes_de_escuchar_y_publica_cada_aviso_valido() -> None:
    abridor = AbridorFalso(
        ConexionFalsa([NotificacionDeCanal(CANAL_CAMBIOS_INCIDENCIAS, VALIDO)], quedarse_abierta=True)
    )
    instalador = InstaladorFalso()
    escuchador, publicar, registro = _escuchador(abridor, instalador)

    await escuchador.iniciar()
    await _esperar(lambda: bool(publicar.publicados))
    await escuchador.detener()

    assert instalador.instalaciones == 1
    assert publicar.publicados == [[CambioDeIncidencia(None, 10, None, 3)]]
    assert ("info", EVENTO_ESCUCHANDO, {}) in registro.eventos
    assert publicar.generales == 0


async def test_un_aviso_sin_contenido_actualiza_a_todos_y_un_canal_ajeno_se_ignora() -> None:
    avisos = [NotificacionDeCanal("otro_canal", VALIDO), NotificacionDeCanal(CANAL_CAMBIOS_INCIDENCIAS, None)]
    escuchador, publicar, _ = _escuchador(AbridorFalso(ConexionFalsa(avisos, quedarse_abierta=True)))

    await escuchador.iniciar()
    await _esperar(lambda: publicar.generales == 1)
    await escuchador.detener()

    assert publicar.publicados == []


@pytest.mark.parametrize("payload", ["{no es json", json.dumps({"areaAntes": 1}), "[]"])
async def test_un_aviso_invalido_se_descarta_con_una_advertencia(payload: str) -> None:
    avisos = [
        NotificacionDeCanal(CANAL_CAMBIOS_INCIDENCIAS, payload),
        NotificacionDeCanal(CANAL_CAMBIOS_INCIDENCIAS, VALIDO),
    ]
    escuchador, publicar, registro = _escuchador(AbridorFalso(ConexionFalsa(avisos, quedarse_abierta=True)))

    await escuchador.iniciar()
    await _esperar(lambda: bool(publicar.publicados))
    await escuchador.detener()

    assert len(publicar.publicados) == 1
    assert any(evento == EVENTO_NOTIFICACION_DESCARTADA for _, evento, _ in registro.eventos)


async def test_si_se_pierde_la_escucha_reintenta_y_al_volver_actualiza_a_todos() -> None:
    primera = ConexionFalsa([_PerdidaDelEnlace()])
    segunda = ConexionFalsa([], quedarse_abierta=True)
    abridor = AbridorFalso(primera, segunda)
    escuchador, publicar, registro = _escuchador(abridor)

    await escuchador.iniciar()
    await _esperar(lambda: publicar.generales == 1)
    await escuchador.detener()

    assert (abridor.aperturas, primera.cerrada, segunda.cerrada) == (2, True, True)
    assert ("warning", EVENTO_ESCUCHA_PERDIDA, {"error": "_PerdidaDelEnlace"}) in registro.eventos


async def test_si_la_conexion_se_cierra_sola_tambien_reintenta() -> None:
    abridor = AbridorFalso(ConexionFalsa([]), ConexionFalsa([], quedarse_abierta=True))
    escuchador, publicar, registro = _escuchador(abridor)

    await escuchador.iniciar()
    await _esperar(lambda: publicar.generales == 1)
    await escuchador.detener()

    assert ("warning", EVENTO_ESCUCHA_PERDIDA, {"error": "ConexionPerdida"}) in registro.eventos


async def test_si_no_se_puede_abrir_la_conexion_reintenta_hasta_lograrlo() -> None:
    abridor = AbridorFalso(_PerdidaDelEnlace(), _PerdidaDelEnlace(), ConexionFalsa([], quedarse_abierta=True))
    escuchador, publicar, _ = _escuchador(abridor)

    await escuchador.iniciar()
    await _esperar(lambda: publicar.generales == 1)
    await escuchador.detener()

    assert abridor.aperturas == 3


async def test_un_cierre_fallido_se_advierte_sin_detener_la_escucha() -> None:
    primera = ConexionFalsa([_PerdidaDelEnlace()])
    primera.falla_al_cerrar = True
    abridor = AbridorFalso(primera, ConexionFalsa([], quedarse_abierta=True))
    escuchador, publicar, registro = _escuchador(abridor)

    await escuchador.iniciar()
    await _esperar(lambda: publicar.generales == 1)
    await escuchador.detener()

    assert ("warning", EVENTO_CIERRE_FALLIDO, {"error": "_PerdidaDelEnlace"}) in registro.eventos


async def test_iniciar_dos_veces_no_duplica_y_detener_cierra_la_conexion() -> None:
    conexion = ConexionFalsa([], quedarse_abierta=True)
    abridor = AbridorFalso(conexion)
    escuchador, _, _ = _escuchador(abridor)

    await escuchador.iniciar()
    await escuchador.iniciar()
    await _esperar(lambda: abridor.aperturas == 1)
    await escuchador.detener()
    await escuchador.detener()

    assert (abridor.aperturas, conexion.cerrada) == (1, True)


async def test_detener_sin_haber_iniciado_no_falla() -> None:
    escuchador, _, _ = _escuchador(AbridorFalso())

    await escuchador.detener()


async def test_si_falla_la_instalacion_el_inicio_falla_y_no_se_escucha() -> None:
    abridor = AbridorFalso()
    escuchador, _, _ = _escuchador(abridor, InstaladorFalso(falla=True))

    with pytest.raises(_PerdidaDelEnlace):
        await escuchador.iniciar()

    assert abridor.aperturas == 0
