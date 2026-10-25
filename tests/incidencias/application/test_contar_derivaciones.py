from app.enums.situacion_derivacion import SituacionDerivacion
from app.incidencias.application.contar_derivaciones import ContarDerivaciones
from app.incidencias.domain.derivaciones import ConteosDeDerivaciones, FiltrosDeDerivaciones
from tests.helpers.derivaciones_en_memoria import DerivacionesEnMemoria


async def test_devuelve_los_conteos_del_lector() -> None:
    lector = DerivacionesEnMemoria()
    lector.conteos = ConteosDeDerivaciones(4, 1, 1, 1, 1)

    conteos = await ContarDerivaciones(lector).execute(FiltrosDeDerivaciones())

    assert conteos == ConteosDeDerivaciones(4, 1, 1, 1, 1)


async def test_la_situacion_se_ignora_pero_los_demas_filtros_se_conservan() -> None:
    lector = DerivacionesEnMemoria()
    filtros = FiltrosDeDerivaciones(situacion=SituacionDerivacion.RESUELTO, texto="000001", establecimiento="1")

    await ContarDerivaciones(lector).execute(filtros)

    assert lector.filtros_contados == [FiltrosDeDerivaciones(texto="000001", establecimiento="1")]
