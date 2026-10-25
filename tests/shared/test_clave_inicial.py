from app.constants.usuarios import CLAVE_INICIAL_ALFABETO, CLAVE_INICIAL_LONGITUD
from app.shared.clave_inicial import generar_clave_inicial


def test_la_clave_tiene_la_longitud_y_el_alfabeto_del_contrato() -> None:
    clave = generar_clave_inicial()

    assert len(clave) == CLAVE_INICIAL_LONGITUD == 20
    assert set(clave) <= set(CLAVE_INICIAL_ALFABETO)


def test_el_alfabeto_omite_los_caracteres_ambiguos() -> None:
    assert not set("IlO01") & set(CLAVE_INICIAL_ALFABETO)


def test_dos_claves_generadas_no_coinciden() -> None:
    assert generar_clave_inicial() != generar_clave_inicial()


def test_acepta_longitud_y_alfabeto_propios() -> None:
    assert generar_clave_inicial(5, "a") == "aaaaa"
