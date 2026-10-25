from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.tipo_area import TipoArea
from app.incidencias.adapters.persistence import consultas, sentencias_de_accion
from app.incidencias.adapters.persistence.mapeo import caso_de
from app.shared.sql_params import ParametrosSql
from app.shared.transaction import transaction

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy import TextClause
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

    from app.enums.categoria_incidencia import CategoriaIncidencia
    from app.enums.motivo_archivo import MotivoArchivo
    from app.enums.resultado_resolucion import ResultadoResolucion
    from app.incidencias.domain.caso_consultado import CasoConsultado
    from app.incidencias.domain.consultas import VisibilidadOperativa


class SqlIncidenciaTransaction:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def _ejecutar(self, sentencia: TextClause, **parametros: object) -> None:
        await self._connection.execute(sentencia, parametros)

    async def _area(self, sentencia: TextClause, tipo: TipoArea, **criterio: object) -> int | None:
        parametros = {**criterio, "tipo": tipo.value, "establecimiento": TipoArea.ESTABLECIMIENTO.value}
        return (await self._connection.execute(sentencia, parametros)).scalar_one_or_none()

    async def buscar_bloqueando(self, codigo: str, visible: VisibilidadOperativa) -> CasoConsultado | None:
        p = ParametrosSql()
        base = consultas.consulta_de_caso(p)
        condiciones = [*consultas.condiciones_base(p, visible), f"i.codigo = {p.agregar(codigo)}"]
        sql = f"{base} WHERE {' AND '.join(condiciones)} FOR UPDATE OF i"
        fila = (await self._connection.execute(text(sql), p.valores)).mappings().first()
        return caso_de(fila) if fila is not None else None

    async def area_receptora_por_id(self, area_id: int, tipo: TipoArea) -> int | None:
        return await self._area(sentencias_de_accion.AREA_RECEPTORA_POR_ID, tipo, area_id=area_id)

    async def area_receptora_por_codigo(self, codigo: str, tipo: TipoArea) -> int | None:
        return await self._area(sentencias_de_accion.AREA_RECEPTORA_POR_CODIGO, tipo, codigo=codigo)

    async def confirmar(self, incidencia_id: str) -> None:
        await self._ejecutar(sentencias_de_accion.CONFIRMAR, incidencia_id=incidencia_id)

    async def corregir(
        self, incidencia_id: str, categoria: CategoriaIncidencia, descripcion_derivacion: str | None
    ) -> None:
        await self._ejecutar(
            sentencias_de_accion.CORREGIR,
            incidencia_id=incidencia_id,
            categoria=categoria.value,
            descripcion=descripcion_derivacion,
        )

    async def derivar(self, incidencia_id: str, area_id: int, descripcion_derivacion: str) -> None:
        await self._ejecutar(
            sentencias_de_accion.DERIVAR,
            incidencia_id=incidencia_id,
            estado=EstadoIncidencia.DERIVADO.value,
            area_id=area_id,
            descripcion=descripcion_derivacion,
        )

    async def cambiar_estado(self, incidencia_id: str, estado: EstadoIncidencia) -> None:
        await self._ejecutar(sentencias_de_accion.CAMBIAR_ESTADO, incidencia_id=incidencia_id, estado=estado.value)

    async def resolver(
        self, incidencia_id: str, medidas_tomadas: str, fundamento: str, resultado: ResultadoResolucion
    ) -> None:
        await self._ejecutar(
            sentencias_de_accion.RESOLVER,
            incidencia_id=incidencia_id,
            medidas_tomadas=medidas_tomadas,
            fundamento=fundamento,
            resultado=resultado.value,
        )

    async def archivar(self, incidencia_id: str, motivo: MotivoArchivo, detalle: str) -> None:
        await self._ejecutar(
            sentencias_de_accion.ARCHIVAR,
            incidencia_id=incidencia_id,
            estado=EstadoIncidencia.ARCHIVADO.value,
            motivo=motivo.value,
            detalle=detalle,
        )

    async def reabrir(self, incidencia_id: str, motivo: str) -> None:
        await self._ejecutar(
            sentencias_de_accion.REABRIR,
            incidencia_id=incidencia_id,
            estado=EstadoIncidencia.EN_GESTION.value,
            motivo=motivo,
        )


class SqlIncidenciaUnitOfWork:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def begin(self, actor: str) -> AsyncIterator[SqlIncidenciaTransaction]:
        async with transaction(self._engine, actor) as connection:
            yield SqlIncidenciaTransaction(connection)
