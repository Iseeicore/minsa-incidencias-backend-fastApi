from typing import TYPE_CHECKING

from app.constants.incidencias import ACTOR_PREFIJO_USUARIO
from app.enums.tipo_area import TipoArea

if TYPE_CHECKING:
    from app.shared.sql_params import ParametrosSql


def envio_humano_desde_otrans(p: ParametrosSql) -> str:
    prefijo = p.agregar(ACTOR_PREFIJO_USUARIO)
    otrans = p.agregar(TipoArea.OTRANS.value)
    establecimiento = p.agregar(TipoArea.ESTABLECIMIENTO.value)
    return f"""
    FROM chatbot.incidencia_paciente_auditoria a
    JOIN catalogo.area origen ON origen.id = CAST(a.cambios #>> '{{area_destino_id,antes}}' AS int)
    JOIN catalogo.tipo_area tipo_origen ON tipo_origen.id = origen.tipo_area_id
    JOIN catalogo.area destino ON destino.id = CAST(a.cambios #>> '{{area_destino_id,despues}}' AS int)
    JOIN catalogo.tipo_area tipo_destino ON tipo_destino.id = destino.tipo_area_id
    WHERE a.incidencia_paciente_id = i.id
      AND a.operacion = 'ACTUALIZACION'
      AND starts_with(a.actor, {prefijo})
      AND NOT jsonb_exists(a.cambios, 'categoria_ia_id')
      AND origen.id <> destino.id
      AND tipo_origen.codigo = {otrans}
      AND tipo_destino.codigo = {establecimiento}"""
