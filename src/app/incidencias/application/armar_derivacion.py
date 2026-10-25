from typing import TYPE_CHECKING

from app.constants.incidencias import CATEGORIA_API, ESTADO_API
from app.constants.textos.derivaciones import DERIVADO_POR_NO_DISPONIBLE
from app.incidencias.domain.casos import AreaDeCaso
from app.incidencias.domain.derivaciones import DerivacionResumen, DestinoDeDerivacion
from app.incidencias.domain.tiempo import a_iso

if TYPE_CHECKING:
    from app.incidencias.domain.derivaciones import DerivacionConsultada


def resumir_derivacion(fila: DerivacionConsultada) -> DerivacionResumen:
    derivado_por = fila.derivado_por if fila.derivado_por is not None else DERIVADO_POR_NO_DISPONIBLE
    return DerivacionResumen(
        id=fila.id,
        codigo_caso=fila.codigo_caso,
        fecha_derivacion=a_iso(fila.fecha_derivacion),
        origen=AreaDeCaso(fila.origen_codigo, fila.origen_nombre),
        destino=DestinoDeDerivacion(fila.destino_codigo, fila.destino_nombre, fila.destino_renipress),
        derivado_por=derivado_por,
        descripcion=fila.descripcion,
        categoria=CATEGORIA_API[fila.categoria] if fila.categoria is not None else None,
        estado=ESTADO_API[fila.estado],
        motivo_archivo=fila.motivo_archivo,
    )
