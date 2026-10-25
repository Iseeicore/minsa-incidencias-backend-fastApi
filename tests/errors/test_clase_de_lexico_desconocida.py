from app.errors.clase_de_lexico_desconocida import ClaseDeLexicoDesconocida


def test_el_error_de_una_clase_inexistente_dice_cual_es_y_es_un_error_de_valor() -> None:
    error = ClaseDeLexicoDesconocida("@fantasma")

    assert isinstance(error, ValueError)
    assert str(error) == "La clase de léxico @fantasma no existe."
