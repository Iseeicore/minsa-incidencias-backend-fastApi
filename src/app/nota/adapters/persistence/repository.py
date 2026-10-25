from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.nota.adapters.persistence.tables import nota_numero_seq, nota_table
from app.nota.domain.codigo_nota import CodigoNota
from app.nota.domain.contenido_nota import ContenidoNota
from app.nota.domain.nota import Nota
from app.nota.domain.titulo_nota import TituloNota
from app.shared.database import translate_database_errors

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


class SqlNotaRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, nota: Nota) -> None:
        valores = {
            "codigo": nota.codigo.valor,
            "titulo": nota.titulo.valor,
            "contenido": nota.contenido.valor,
            "creada_en": nota.creada_en,
        }
        with translate_database_errors():
            async with self._engine.begin() as connection:
                await connection.execute(insert(nota_table).values(**valores))

    async def find_by_codigo(self, codigo: CodigoNota) -> Nota | None:
        with translate_database_errors():
            async with self._engine.connect() as connection:
                resultado = await connection.execute(select(nota_table).where(nota_table.c.codigo == codigo.valor))
                fila = resultado.first()
        if fila is None:
            return None
        return Nota(
            codigo=CodigoNota(fila.codigo),
            titulo=TituloNota(fila.titulo),
            contenido=ContenidoNota(fila.contenido),
            creada_en=fila.creada_en,
        )


class SqlCodeGenerator:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def next_codigo(self) -> CodigoNota:
        with translate_database_errors():
            async with self._engine.begin() as connection:
                numero = (await connection.execute(select(nota_numero_seq.next_value()))).scalar_one()
        return CodigoNota.desde_numero(numero)
