from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.situacion_derivacion import SituacionDerivacion
from app.incidencias.adapters.persistence import consultas_de_derivacion as consultas
from app.incidencias.domain.derivaciones import FiltrosDeDerivaciones
from app.shared.sql_params import ParametrosSql


def _valores(p: ParametrosSql) -> list[object]:
    return list(p.valores.values())


def test_el_ultimo_envio_se_elige_por_fecha_e_id_y_trae_la_categoria_con_la_que_se_envio() -> None:
    sql = consultas.desde_ultimo_envio(ParametrosSql())

    assert "ORDER BY a.fecha_hora DESC, a.id DESC LIMIT 1" in sql
    assert ") envio ON true" in sql
    assert "h.id <= envio.id" in sql
    assert "jsonb_exists(h.cambios, 'categoria_id')" in sql
    assert "establecimiento.area_id = envio.destino_id" in sql


def test_sin_filtros_solo_se_piden_casos_activos_de_un_estado_conocido() -> None:
    p = ParametrosSql()

    condiciones = consultas.condiciones_de_derivacion(p, FiltrosDeDerivaciones(), con_situacion=True)

    assert condiciones[0] == "i.activo"
    assert len(condiciones) == 2
    assert condiciones[1].startswith("e.codigo = ANY(CAST(:p0 AS text[]))")


def test_cada_filtro_agrega_su_condicion_con_su_parametro() -> None:
    p = ParametrosSql()
    filtros = FiltrosDeDerivaciones(
        situacion=SituacionDerivacion.PENDIENTE,
        texto="10%",
        establecimiento="1234",
        categoria=CategoriaIncidencia.QUEJA,
        desde="2026-03-10",
        hasta="2026-03-11",
    )

    condiciones = consultas.condiciones_de_derivacion(p, filtros, con_situacion=True)

    assert len(condiciones) == 8
    assert _valores(p)[1:] == [
        ["REGISTRADO", "CLASIFICADO", "DERIVADO"],
        "%10\\%%",
        "1234",
        "QUEJA",
        "2026-03-10",
        "2026-03-11",
    ]
    assert any("ILIKE" in condicion and "ESCAPE" in condicion for condicion in condiciones)
    assert any(condicion.startswith("envio.fecha_hora >= (") for condicion in condiciones)
    assert any(condicion.startswith("envio.fecha_hora < ((") for condicion in condiciones)
    assert all("America/Lima" in condicion for condicion in condiciones if "fecha_hora" in condicion)


def test_los_conteos_ignoran_la_situacion_aunque_venga_en_los_filtros() -> None:
    p = ParametrosSql()

    condiciones = consultas.condiciones_de_derivacion(
        p, FiltrosDeDerivaciones(situacion=SituacionDerivacion.RESUELTO), con_situacion=False
    )

    assert len(condiciones) == 2


def test_las_columnas_traen_el_envio_el_usuario_que_lo_hizo_y_la_descripcion_de_ese_momento() -> None:
    p = ParametrosSql()

    sql = consultas.columnas_de_derivacion(p)

    assert _valores(p)[0] == "usuario:"
    assert sql.lstrip().startswith("SELECT CAST(envio.id AS text) AS id")
    assert "ui.nombre_completo AS derivado_por" in sql
    assert "jsonb_exists(h.cambios, 'derivacion_descripcion')" in sql
    assert "'{derivacion_descripcion,despues}'" in sql
    assert "envio.actor = :p0 || ui.correo" in sql
