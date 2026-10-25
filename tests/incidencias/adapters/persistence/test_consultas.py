from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.incidencias.adapters.persistence import consultas
from app.incidencias.domain.consultas import (
    FiltrosCasos,
    VisibilidadDeDerivaciones,
    VisibilidadDeIpress,
    VisibilidadOperativa,
)
from app.shared.permisos import PERMISOS_POR_ROL, ReglaDeAccion
from app.shared.sql_params import ParametrosSql

VISIBLE = VisibilidadOperativa(("GESTOR", "OTRANS"), ver_sin_categoria=True, area_id=7)


def _valores(p: ParametrosSql) -> list[object]:
    return list(p.valores.values())


def test_la_visibilidad_lleva_roles_area_y_permiso_de_sin_categoria_como_parametros() -> None:
    p = ParametrosSql()

    sql = consultas.visibilidad(p, VISIBLE)

    assert _valores(p) == [["GESTOR", "OTRANS"], True, 7, ["ESTABLECIMIENTO", "DIRIS"]]
    assert "gestion.rol_categoria" in sql
    assert "k.es_sensible" in sql
    assert sql.count("CAST(:p") == 4


def test_las_condiciones_base_exigen_activo_estado_conocido_y_visibilidad() -> None:
    p = ParametrosSql()

    condiciones = consultas.condiciones_base(p, VISIBLE)

    assert condiciones[0] == "i.activo"
    assert condiciones[1].startswith("e.codigo = ANY(CAST(:p0 AS text[]))")
    assert _valores(p)[0] == [estado.value for estado in EstadoIncidencia]


def test_sin_filtros_no_hay_condiciones_de_filtro() -> None:
    assert consultas.condiciones_de_filtros(ParametrosSql(), FiltrosCasos()) == []


def test_cada_filtro_agrega_su_condicion_con_su_parametro() -> None:
    p = ParametrosSql()
    filtros = FiltrosCasos(
        estado=EstadoIncidencia.DERIVADO,
        categoria=CategoriaIncidencia.QUEJA,
        texto="100%",
        establecimiento="1234",
        motivo_archivo=MotivoArchivo.NO_CORRESPONDE,
        desde="2026-03-10",
        hasta="2026-03-11",
    )

    condiciones = consultas.condiciones_de_filtros(p, filtros)

    assert len(condiciones) == 7
    assert _valores(p) == ["1234", "DERIVADO", "NO_CORRESPONDE", "QUEJA", "2026-03-10", "2026-03-11", "%100\\%%"]
    assert any("AT TIME ZONE 'America/Lima'" in condicion for condicion in condiciones)
    assert any("ILIKE" in condicion and "ESCAPE" in condicion for condicion in condiciones)


def test_sin_categoria_filtra_los_que_no_tienen() -> None:
    assert consultas.condiciones_de_filtros(ParametrosSql(), FiltrosCasos(sin_categoria=True)) == [
        "i.categoria_id IS NULL"
    ]


def test_el_filtro_de_plazo_pide_abiertos_que_vencen_pronto_y_aun_no_vencidos() -> None:
    p = ParametrosSql()

    condiciones = consultas.condiciones_de_filtros(p, FiltrosCasos(aviso_horas=48))

    assert len(condiciones) == 3
    assert "<= now() + make_interval" in condiciones[1]
    assert condiciones[2].endswith("> now()")
    assert _valores(p)[1] == 48


def test_la_condicion_de_por_vencer_incluye_vencidos_salvo_que_se_pida_lo_contrario() -> None:
    con_vencidos = consultas.condiciones_por_vencer(ParametrosSql(), 48)
    sin_vencidos = consultas.condiciones_por_vencer(ParametrosSql(), 48, sin_vencidos=True)

    assert len(con_vencidos) == 2
    assert len(sin_vencidos) == 3


def test_sin_reglas_pendientes_no_se_restringe_y_con_reglas_vacias_no_hay_casos() -> None:
    assert consultas.condicion_de_pendientes(ParametrosSql(), None) == []
    assert consultas.condicion_de_pendientes(ParametrosSql(), ()) == ["false"]


def test_las_reglas_pendientes_se_combinan_con_or_y_llevan_estado_categoria_y_revision() -> None:
    p = ParametrosSql()
    reglas: tuple[ReglaDeAccion, ...] = PERMISOS_POR_ROL["GESTOR"].acciones[:2]

    [condicion] = consultas.condicion_de_pendientes(p, reglas)

    assert condicion.startswith("(")
    assert " OR " in condicion
    assert "c.codigo = ANY(" in condicion
    assert "categoria_corregida_en IS NOT NULL" in condicion
    assert False in _valores(p)


def test_la_consulta_de_caso_lleva_los_prefijos_de_actor_como_parametros() -> None:
    p = ParametrosSql()

    sql = consultas.consulta_de_caso(p)

    assert _valores(p) == ["DERIVADO", "usuario:", "sistema:"]
    assert "catalogo.sumar_dias_habiles" in sql
    assert "'{estado_incidencia_id,despues}'" in sql
    assert "AS vence_atencion_en" in sql


def test_la_visibilidad_de_un_establecimiento_filtra_por_su_identificador() -> None:
    p = ParametrosSql()

    sql = consultas.visibilidad(p, VisibilidadDeIpress(establecimiento_id=9))

    assert sql == "i.establecimiento_id = CAST(:p0 AS int)"
    assert _valores(p) == [9]


def test_la_visibilidad_del_seguimiento_pide_un_envio_humano_de_otrans_a_un_establecimiento() -> None:
    p = ParametrosSql()

    sql = consultas.visibilidad(p, VisibilidadDeDerivaciones())

    assert sql.startswith("EXISTS (SELECT 1")
    assert "tipo_origen.codigo = :p1" in sql
    assert _valores(p) == ["usuario:", "OTRANS", "ESTABLECIMIENTO"]
