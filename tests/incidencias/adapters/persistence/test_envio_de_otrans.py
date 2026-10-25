from app.incidencias.adapters.persistence.envio_de_otrans import envio_humano_desde_otrans
from app.shared.sql_params import ParametrosSql


def test_el_envio_humano_pide_un_cambio_de_area_hecho_por_un_usuario_de_otrans_a_un_establecimiento() -> None:
    p = ParametrosSql()

    sql = envio_humano_desde_otrans(p)

    assert list(p.valores.values()) == ["usuario:", "OTRANS", "ESTABLECIMIENTO"]
    assert "a.operacion = 'ACTUALIZACION'" in sql
    assert "starts_with(a.actor, CAST" not in sql
    assert "starts_with(a.actor, :p0)" in sql
    assert "origen.id <> destino.id" in sql
    assert "NOT jsonb_exists(a.cambios, 'categoria_ia_id')" in sql
    assert "tipo_origen.codigo = :p1" in sql
    assert "tipo_destino.codigo = :p2" in sql


def test_el_envio_lee_el_area_de_antes_y_de_despues_del_cambio() -> None:
    sql = envio_humano_desde_otrans(ParametrosSql())

    assert "'{area_destino_id,antes}'" in sql
    assert "'{area_destino_id,despues}'" in sql
    assert "a.incidencia_paciente_id = i.id" in sql
