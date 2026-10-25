from app.shared.correo import normalizar_correo


def test_el_correo_se_recorta_y_se_pasa_a_minusculas() -> None:
    assert normalizar_correo("  ANA@Minsa.GOB.pe \n") == "ana@minsa.gob.pe"
