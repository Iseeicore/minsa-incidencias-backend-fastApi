import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.rol_codigo import RolCodigo
from app.eventos.adapters.persistence.categorias import SqlCategoriasPorRol
from tests.helpers.base import consultar

pytestmark = pytest.mark.integration


async def _id_de(engine: AsyncEngine, categoria: CategoriaIncidencia) -> int:
    [(identificador,)] = await consultar(
        engine, "SELECT id FROM catalogo.categoria_incidencia WHERE codigo = :codigo", codigo=categoria.value
    )
    return int(str(identificador))


async def test_lee_las_categorias_de_cada_rol_activo(engine: AsyncEngine) -> None:
    por_rol = await SqlCategoriasPorRol(engine).categorias_por_rol()
    corrupcion = await _id_de(engine, CategoriaIncidencia.DENUNCIA_CORRUPCION)
    queja = await _id_de(engine, CategoriaIncidencia.QUEJA)

    assert por_rol[RolCodigo.OTRANS] == {corrupcion}
    assert corrupcion not in por_rol[RolCodigo.ESTABLECIMIENTO]
    assert queja in por_rol[RolCodigo.GESTOR]
    assert set(por_rol) >= {RolCodigo.ADMINISTRADOR, RolCodigo.GESTOR, RolCodigo.ESTABLECIMIENTO, RolCodigo.OTRANS}
