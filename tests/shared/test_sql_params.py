from app.shared.sql_params import ParametrosSql


def test_cada_valor_recibe_un_nombre_nuevo_y_queda_guardado() -> None:
    parametros = ParametrosSql()

    primero = parametros.agregar("a")
    segundo = parametros.agregar(2)

    assert (primero, segundo) == (":p0", ":p1")
    assert parametros.valores == {"p0": "a", "p1": 2}


def test_con_tipo_envuelve_el_marcador_en_un_cast() -> None:
    parametros = ParametrosSql()

    assert parametros.con_tipo(["x"], "text[]") == "CAST(:p0 AS text[])"
    assert parametros.valores == {"p0": ["x"]}


def test_dos_constructores_no_comparten_valores() -> None:
    uno, otro = ParametrosSql(), ParametrosSql()
    uno.agregar(1)

    assert otro.valores == {}
