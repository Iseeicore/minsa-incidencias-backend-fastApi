import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.enums.categoria_api import CategoriaApi
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.filtro_corrupcion.adapters.persistence.clasificador import SqlClasificadorUnitOfWork
from app.filtro_corrupcion.application.clasificar_incidencias import ClasificadorIncidencias, vaciar_cola
from app.incidencias.adapters.persistence.analisis import SqlAnalisisReader
from app.incidencias.application.armar_analisis import armar_analisis
from tests.helpers.casos import sembrar_caso

pytestmark = pytest.mark.integration

TEXTO_COBRO = "El director del hospital me pidió plata para atenderme"


async def test_lo_que_escribe_el_clasificador_lo_lee_la_consulta_del_analisis_sin_perder_nada(
    engine: AsyncEngine,
) -> None:
    caso = await sembrar_caso(engine, categoria=None, marcador=TEXTO_COBRO)
    await vaciar_cola(ClasificadorIncidencias(SqlClasificadorUnitOfWork(engine)))

    fila = await SqlAnalisisReader(engine).buscar(caso.id)

    assert fila is not None
    analisis = armar_analisis(caso.codigo, fila)
    assert analisis.categoria_ia == CategoriaApi.DENUNCIA_CORRUPCION
    assert analisis.propuesta_del_analisis == CategoriaApi.DENUNCIA_CORRUPCION
    assert analisis.motivo_de_escritura == MotivoDeEscritura.REGLAS
    assert analisis.version_clasificador is not None
    assert analisis.version_clasificador.endswith("+coincidencias-v1")
    assert analisis.explicacion is not None
    assert analisis.explicacion.startswith("Categoría propuesta: Denuncia por corrupción.")
    assert analisis.etiqueta_normas == "Referencia orientativa; la califica OTRANS."
    assert [cita.fragmento_id for cita in analisis.supuestos] == ["ANEXO_C-III-b"]
    assert analisis.procedimiento
    assert analisis.cargo_mencionado == "director del hospital"
    assert analisis.senales
    assert (analisis.modelo.variante, analisis.modelo.degradado, analisis.modelo.peso_ia) == (None, False, None)
    assert analisis.requiere_revision_humana is True
