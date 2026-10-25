from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.filtro_corrupcion.domain.cola_de_clasificacion import (
        AnalisisAGuardar,
        CasoPendiente,
        CategoriaAEscribir,
        FilaAlarma,
    )
    from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia


class AlmacenDelClasificador:
    def __init__(self, cola: list[CasoPendiente] | None = None) -> None:
        self.cola = list(cola or [])
        self.areas: dict[str, int] = {}
        self.candidatos: list[CandidatoCoincidencia] = []
        self.analisis: list[AnalisisAGuardar] = []
        self.categorias: list[CategoriaAEscribir] = []
        self.actores: list[str] = []
        self.consultas: list[tuple[tuple[str, ...], tuple[str, ...] | None]] = []
        self.busquedas: list[tuple[str, str]] = []
        self.falla_al_consultar_la_cola: Exception | None = None
        self.falla_al_guardar: Exception | None = None
        self.fila_de_alarma: FilaAlarma | None = None
        self.consultas_de_alarma: list[tuple[int, int]] = []

    @asynccontextmanager
    async def begin(self, actor: str) -> AsyncIterator[_Transaccion]:
        self.actores.append(actor)
        transaccion = _Transaccion(self)
        yield transaccion
        self.analisis.extend(transaccion.analisis)
        self.categorias.extend(transaccion.categorias)
        escritas = {categoria.incidencia_id for categoria in transaccion.categorias}
        self.cola = [caso for caso in self.cola if caso.id not in escritas]

    async def alarma_sin_clasificar(self, minutos: int, codigos_maximos: int) -> FilaAlarma | None:
        self.consultas_de_alarma.append((minutos, codigos_maximos))
        return self.fila_de_alarma


class _Transaccion:
    def __init__(self, almacen: AlmacenDelClasificador) -> None:
        self._almacen = almacen
        self.analisis: list[AnalisisAGuardar] = []
        self.categorias: list[CategoriaAEscribir] = []

    async def siguiente_pendiente(
        self, abandonados: tuple[str, ...], solo_casos: tuple[str, ...] | None
    ) -> CasoPendiente | None:
        self._almacen.consultas.append((abandonados, solo_casos))
        if self._almacen.falla_al_consultar_la_cola is not None:
            raise self._almacen.falla_al_consultar_la_cola
        for caso in self._almacen.cola:
            if caso.id not in abandonados and (solo_casos is None or caso.id in solo_casos):
                return caso
        return None

    async def area_mencionada(self, codigo: str) -> int | None:
        return self._almacen.areas.get(codigo)

    async def buscar_coincidencias(self, incidencia_id: str, texto: str) -> list[CandidatoCoincidencia]:
        self._almacen.busquedas.append((incidencia_id, texto))
        return list(self._almacen.candidatos)

    async def registrar_analisis(self, analisis: AnalisisAGuardar) -> None:
        self.analisis.append(analisis)

    async def actualizar_categoria(self, categoria: CategoriaAEscribir) -> None:
        if self._almacen.falla_al_guardar is not None:
            raise self._almacen.falla_al_guardar
        self.categorias.append(categoria)
