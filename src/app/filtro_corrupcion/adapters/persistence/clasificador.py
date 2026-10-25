import json
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.exc import ProgrammingError

from app.constants.clasificacion import (
    CANDIDATOS_MAXIMOS_COINCIDENCIA,
    EJEMPLOS_RECIENTES_MAXIMOS,
    SIMILITUD_MINIMA_CANDIDATO,
)
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.filtro_corrupcion.adapters.persistence import sentencias_del_clasificador as sentencias
from app.filtro_corrupcion.adapters.persistence.senales_json import senales_a_json
from app.filtro_corrupcion.domain.cola_de_clasificacion import CasoPendiente, FilaAlarma
from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia
from app.shared.texto_js import recortar_como_js
from app.shared.transaction import transaction

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

    from app.filtro_corrupcion.domain.cola_de_clasificacion import AnalisisAGuardar, CategoriaAEscribir

RELACION_NO_DISPONIBLE = "42P01"
FUNCION_NO_DISPONIBLE = "42883"
CATEGORIAS_DE_COINCIDENCIA = [categoria.value for categoria in CategoriaIncidencia]


def _falta_soporte_opcional(error: ProgrammingError) -> bool:
    return getattr(error.orig, "sqlstate", None) in {RELACION_NO_DISPONIBLE, FUNCION_NO_DISPONIBLE}


class SqlClasificadorTransaction:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def siguiente_pendiente(
        self, abandonados: tuple[str, ...], solo_casos: tuple[str, ...] | None
    ) -> CasoPendiente | None:
        parametros = {
            "estado": EstadoIncidencia.REGISTRADO.value,
            "abandonados": list(abandonados),
            "solo": list(solo_casos) if solo_casos is not None else None,
        }
        fila = (await self._connection.execute(sentencias.SIGUIENTE_PENDIENTE, parametros)).mappings().first()
        if fila is None:
            return None
        return CasoPendiente(str(fila["id"]), fila["codigo"], fila["descripcion"], fila["establecimiento"])

    async def area_mencionada(self, codigo: str) -> int | None:
        resultado = await self._connection.execute(sentencias.AREA_MENCIONADA, {"codigo": codigo})
        return resultado.scalar_one_or_none()

    async def buscar_coincidencias(self, incidencia_id: str, texto: str) -> list[CandidatoCoincidencia]:
        if recortar_como_js(texto) == "":
            return []
        parametros = {
            "incidencia": incidencia_id,
            "texto": texto,
            "minima": SIMILITUD_MINIMA_CANDIDATO,
            "maximo": CANDIDATOS_MAXIMOS_COINCIDENCIA,
            "categorias": CATEGORIAS_DE_COINCIDENCIA,
            "ejemplos": EJEMPLOS_RECIENTES_MAXIMOS,
        }
        try:
            async with self._connection.begin_nested():
                filas = (await self._connection.execute(sentencias.COINCIDENCIAS, parametros)).all()
        except ProgrammingError as error:
            if _falta_soporte_opcional(error):
                return []
            raise
        return [CandidatoCoincidencia(CategoriaIncidencia(fila.categoria), fila.similitud) for fila in filas]

    async def registrar_analisis(self, analisis: AnalisisAGuardar) -> None:
        await self._connection.execute(
            sentencias.INSERTAR_ANALISIS,
            {
                "incidencia": analisis.incidencia_id,
                "version_reglas": analisis.version_reglas,
                "puntaje": analisis.puntaje,
                "senales": json.dumps(senales_a_json(analisis.senales), ensure_ascii=False),
                "cargo": analisis.cargo_mencionado,
                "area": analisis.area_mencionada_id,
                "nombre": analisis.nombre_mencionado,
            },
        )

    async def actualizar_categoria(self, categoria: CategoriaAEscribir) -> None:
        await self._connection.execute(
            sentencias.ACTUALIZAR_CATEGORIA,
            {
                "incidencia": categoria.incidencia_id,
                "categoria": categoria.categoria.value,
                "confianza": categoria.confianza,
                "version": categoria.version,
            },
        )


class SqlClasificadorUnitOfWork:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def begin(self, actor: str) -> AsyncIterator[SqlClasificadorTransaction]:
        async with transaction(self._engine, actor) as connection:
            yield SqlClasificadorTransaction(connection)


class SqlAlarmaReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def alarma_sin_clasificar(self, minutos: int, codigos_maximos: int) -> FilaAlarma | None:
        parametros = {"estado": EstadoIncidencia.REGISTRADO.value, "minutos": minutos, "maximo": codigos_maximos}
        async with self._engine.connect() as connection:
            fila = (await connection.execute(sentencias.ALARMA_SIN_CLASIFICAR, parametros)).first()
        if fila is None:
            return None
        return FilaAlarma(fila.atrasados, fila.minutos, tuple(fila.codigos or ()))
