from typing import TYPE_CHECKING

from app.constants.derivaciones import ESTADOS_DE_DERIVACION
from app.constants.incidencias import ACTOR_PREFIJO_USUARIO, ZONA_DE_LIMA
from app.incidencias.adapters.persistence.consultas import ESCAPE_DE_LIKE, ESTADOS_CONOCIDOS
from app.incidencias.adapters.persistence.envio_de_otrans import envio_humano_desde_otrans
from app.shared.text_search import like_pattern

if TYPE_CHECKING:
    from app.incidencias.domain.derivaciones import FiltrosDeDerivaciones
    from app.shared.sql_params import ParametrosSql


def desde_ultimo_envio(p: ParametrosSql) -> str:
    return f"""
    FROM chatbot.incidencia_paciente i
    JOIN catalogo.estado_incidencia e ON e.id = i.estado_incidencia_id
    JOIN LATERAL (
      SELECT a.id, a.actor, a.fecha_hora,
             origen.codigo AS origen_codigo, origen.nombre AS origen_nombre,
             destino.id AS destino_id, destino.codigo AS destino_codigo, destino.nombre AS destino_nombre
      {envio_humano_desde_otrans(p)}
      ORDER BY a.fecha_hora DESC, a.id DESC LIMIT 1
    ) envio ON true
    LEFT JOIN LATERAL (
      SELECT CASE WHEN h.operacion = 'CREACION' THEN h.cambios ->> 'categoria_id'
                  ELSE h.cambios #>> '{{categoria_id,despues}}' END AS categoria_id
      FROM chatbot.incidencia_paciente_auditoria h
      WHERE h.incidencia_paciente_id = i.id AND h.id <= envio.id AND jsonb_exists(h.cambios, 'categoria_id')
      ORDER BY h.id DESC LIMIT 1
    ) categoria_enviada ON true
    LEFT JOIN catalogo.categoria_incidencia c ON c.id = CAST(categoria_enviada.categoria_id AS smallint)
    LEFT JOIN catalogo.establecimiento_salud establecimiento ON establecimiento.area_id = envio.destino_id"""


def condiciones_de_derivacion(p: ParametrosSql, filtros: FiltrosDeDerivaciones, *, con_situacion: bool) -> list[str]:
    condiciones = ["i.activo", f"e.codigo = ANY({p.con_tipo(ESTADOS_CONOCIDOS, 'text[]')})"]
    if con_situacion and filtros.situacion:
        estados = [estado.value for estado in ESTADOS_DE_DERIVACION[filtros.situacion]]
        condiciones.append(f"e.codigo = ANY({p.con_tipo(estados, 'text[]')})")
    if filtros.texto:
        condiciones.append(f"i.codigo ILIKE {p.agregar(like_pattern(filtros.texto))} {ESCAPE_DE_LIKE}")
    if filtros.establecimiento:
        condiciones.append(f"establecimiento.codigo_renipress = {p.agregar(filtros.establecimiento)}")
    if filtros.categoria:
        condiciones.append(f"c.codigo = {p.agregar(filtros.categoria.value)}")
    if filtros.desde:
        desde = p.con_tipo(filtros.desde, "date")
        condiciones.append(f"envio.fecha_hora >= ({desde})::timestamp AT TIME ZONE '{ZONA_DE_LIMA}'")
    if filtros.hasta:
        hasta = p.con_tipo(filtros.hasta, "date")
        condiciones.append(f"envio.fecha_hora < (({hasta}) + 1)::timestamp AT TIME ZONE '{ZONA_DE_LIMA}'")
    return condiciones


def columnas_de_derivacion(p: ParametrosSql) -> str:
    prefijo = p.agregar(ACTOR_PREFIJO_USUARIO)
    return f"""SELECT CAST(envio.id AS text) AS id, i.codigo AS codigo_caso, envio.fecha_hora AS fecha_derivacion,
    envio.origen_codigo, envio.origen_nombre, envio.destino_codigo, envio.destino_nombre,
    establecimiento.codigo_renipress AS destino_renipress, ui.nombre_completo AS derivado_por,
    descripcion.valor AS descripcion, c.codigo AS categoria, e.codigo AS estado, ma.codigo AS motivo_archivo
    {desde_ultimo_envio(p)}
    LEFT JOIN gestion.usuario_interno ui ON envio.actor = {prefijo} || ui.correo
    LEFT JOIN catalogo.motivo_archivo ma ON ma.id = i.motivo_archivo_id
    LEFT JOIN LATERAL (
      SELECT CASE WHEN h.operacion = 'CREACION' THEN h.cambios ->> 'derivacion_descripcion'
                  ELSE h.cambios #>> '{{derivacion_descripcion,despues}}' END AS valor
      FROM chatbot.incidencia_paciente_auditoria h
      WHERE h.incidencia_paciente_id = i.id AND h.id <= envio.id AND jsonb_exists(h.cambios, 'derivacion_descripcion')
      ORDER BY h.id DESC LIMIT 1
    ) descripcion ON true"""
